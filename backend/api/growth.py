"""World access only. Independent of referral, XP and money ledgers."""
import os,time,secrets
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import String,Float,ForeignKey,UniqueConstraint,select,func
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base,get_db
from .models import User,uid,Analytics
from .auth import current_user,require_admin
from .core import Strict,check_city,emit
router=APIRouter(prefix='/api/growth')
STARTER_LIMIT=4
SHARE_GOAL=4
CHANNELS={'whatsapp','facebook','instagram','x','email','sms','copy','native','more'}

class WorldAccess(Base):
 __tablename__='world_access'
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
 destination_id:Mapped[str]=mapped_column(String(80),primary_key=True)
 source:Mapped[str]=mapped_column(String(20))
 created_at:Mapped[float]=mapped_column(Float,default=time.time)

class ShareInvite(Base):
 __tablename__='world_share_invites'
 code:Mapped[str]=mapped_column(String(40),primary_key=True,default=lambda:secrets.token_urlsafe(18))
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 destination_id:Mapped[str]=mapped_column(String(80))
 created_at:Mapped[float]=mapped_column(Float,default=time.time)
 __table_args__=(UniqueConstraint('user_id','destination_id'),)

class ShareAction(Base):
 __tablename__='world_share_actions'
 id:Mapped[str]=mapped_column(String(36),primary_key=True)
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 destination_id:Mapped[str]=mapped_column(String(80))
 channel:Mapped[str]=mapped_column(String(20))
 outcome:Mapped[str]=mapped_column(String(20))
 created_at:Mapped[float]=mapped_column(Float,default=time.time,index=True)

class GrowthEvent(Base):
 __tablename__='world_growth_events'
 id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
 user_id:Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True,index=True)
 kind:Mapped[str]=mapped_column(String(50),index=True)
 destination_id:Mapped[str]=mapped_column(String(80),default='')
 channel:Mapped[str]=mapped_column(String(20),default='')
 invite_code:Mapped[str]=mapped_column(String(40),default='')
 created_at:Mapped[float]=mapped_column(Float,default=time.time,index=True)

def event(db,u,kind,destination='',channel='',code=''):
 if u and u.analytics_consent:db.add(GrowthEvent(user_id=u.id,kind=kind,destination_id=destination,channel=channel,invite_code=code))
def lock(db,u):db.scalar(select(User.id).where(User.id==u.id).with_for_update())
def count(db,u):return min(STARTER_LIMIT,db.scalar(select(func.count()).select_from(WorldAccess).where(WorldAccess.user_id==u.id)) or 0)
def progress(db,u,d):return min(SHARE_GOAL,db.scalar(select(func.count()).select_from(ShareAction).where(ShareAction.user_id==u.id,ShareAction.destination_id==d)) or 0)
def access(db,u,d):return db.get(WorldAccess,(u.id,d))
def require_open(db,d):
 from .discovery import catalog
 if not any(c['id']==d and c.get('enabled') and c.get('public',True) and c.get('joinable',True) for c in catalog(db)):raise HTTPException(403,'This world is not currently open')
def locked(db,u,d):
 used=count(db,u)
 return {'code':'STARTER_CONFIRMATION_REQUIRED' if used<STARTER_LIMIT else 'WORLD_LOCKED','destination_id':d,'starter_selected':used,'starter_remaining':STARTER_LIMIT-used,'shares':progress(db,u,d),'share_goal':SHARE_GOAL,'message':'Choose this as a free Starter World.' if used<STARTER_LIMIT else 'Share Mindaam 4 times to unlock this world.'}
def require_access(db,u,d):
 from .discovery import catalog
 if not any(c['id']==d and c.get('enabled') and c.get('public',True) and c.get('joinable',True) for c in catalog(db)):raise HTTPException(403,'This world is not currently open')
 if not access(db,u,d):raise HTTPException(403,locked(db,u,d))
def select_starter(db,u,d,confirmed=False):
 check_city(d);lock(db,u)
 from .discovery import catalog
 if not any(c['id']==d and all(c.get(k,True) for k in ['enabled','public','joinable']) for c in catalog(db)):raise HTTPException(403,'World unavailable')
 if access(db,u,d):return
 used=count(db,u)
 if used>=STARTER_LIMIT:raise HTTPException(403,locked(db,u,d))
 if not confirmed:raise HTTPException(409,locked(db,u,d))
 db.add(WorldAccess(user_id=u.id,destination_id=d,source='starter'));db.flush()
 event(db,u,'starter_world_selected',d);event(db,u,f'starter_world_number_{used+1}',d)
 if used+1==STARTER_LIMIT:event(db,u,'four_worlds_completed',d)

def state(db,u):
 from .discovery import cities
 rows=[c for c in cities(db) if c.get('enabled') and c.get('public',True) and c.get('joinable',True)]
 owned={a.destination_id:a for a in db.scalars(select(WorldAccess).where(WorldAccess.user_id==u.id))}
 shares=dict(db.execute(select(ShareAction.destination_id,func.count()).where(ShareAction.user_id==u.id).group_by(ShareAction.destination_id)).all());used=count(db,u)
 hot=max(1,int(os.getenv('WORLD_HOT_ONLINE','20')));active=max(1,int(os.getenv('WORLD_ACTIVE_ONLINE','3')))
 return {'starter_selected':used,'starter_limit':STARTER_LIMIT,'starter_remaining':STARTER_LIMIT-used,'share_goal':SHARE_GOAL,'cooldown_seconds':cooldown(),'worlds':[{**c,'access':'owned' if c['id'] in owned else 'free' if used<STARTER_LIMIT else 'locked','source':owned[c['id']].source if c['id'] in owned else None,'shares':min(SHARE_GOAL,shares.get(c['id'],0)),'activity':'HOT NOW' if c['online']>=hot else 'ACTIVE' if c['online']>=active else None} for c in rows]}
@router.get('/worlds')
def worlds(u=Depends(current_user),db=Depends(get_db)):return state(db,u)
class Choice(Strict):
 confirmed:bool=False
@router.post('/worlds/{destination}/starter')
def choose(destination:str,data:Choice,u=Depends(current_user),db=Depends(get_db)):
 select_starter(db,u,destination,data.confirmed);return state(db,u)

@router.post('/worlds/{destination}/invite')
def invite(destination:str,u=Depends(current_user),db=Depends(get_db)):
 check_city(destination);lock(db,u);require_open(db,destination)
 row=db.scalar(select(ShareInvite).where(ShareInvite.user_id==u.id,ShareInvite.destination_id==destination))
 if not row:row=ShareInvite(user_id=u.id,destination_id=destination);db.add(row);db.flush()
 event(db,u,'share_unlock_started',destination)
 return {'code':row.code,'path':'/join/'+row.code,'destination_id':destination}
@router.get('/invites/{code}')
def invite_info(code:str,db=Depends(get_db)):
 row=db.get(ShareInvite,code)
 if not row:raise HTTPException(404,'Invite not found')
 from .discovery import cities
 world=next((c for c in cities(db) if c['id']==row.destination_id and c['enabled']),None)
 if not world:raise HTTPException(404,'World unavailable')
 return {'destination':world,'code':row.code} # Never expose sharer identity.

def cooldown():return max(1,min(60,int(os.getenv('WORLD_SHARE_COOLDOWN_SECONDS','5'))))
class ShareInput(Strict):
 share_action_id:UUID
 channel:str=Field(max_length=20)
 outcome:str=Field(max_length=20)
 invite_code:str=Field(max_length=40)
@router.post('/worlds/{destination}/share')
def share(destination:str,data:ShareInput,u=Depends(current_user),db=Depends(get_db)):
 check_city(destination);lock(db,u);require_open(db,destination)
 if data.channel not in CHANNELS or data.outcome not in {'opened','copied','shared','handoff'}:raise HTTPException(422,'Unsupported share action')
 if data.outcome=='handoff' and data.channel not in {'email','sms'}:raise HTTPException(422,'Unsupported app handoff')
 if data.channel=='copy' and data.outcome!='copied' or data.channel in {'native','more','instagram'} and data.outcome not in {'shared','copied'}:raise HTTPException(422,'Share was not completed or copied')
 prior=db.get(ShareAction,str(data.share_action_id))
 if prior:
  if prior.user_id!=u.id or prior.destination_id!=destination or prior.channel!=data.channel:raise HTTPException(409,'Share action already used')
  return {**state(db,u),'counted':False,'duplicate':True}
 inv=db.get(ShareInvite,data.invite_code)
 if not inv or inv.user_id!=u.id or inv.destination_id!=destination:raise HTTPException(403,'Create an invite for this world first')
 owned=bool(access(db,u,destination))
 if not owned and count(db,u)<STARTER_LIMIT:raise HTTPException(409,'Use your remaining free world choices first')
 latest=db.scalar(select(ShareAction).where(ShareAction.user_id==u.id).order_by(ShareAction.created_at.desc()).limit(1))
 if latest and time.time()-latest.created_at<cooldown():raise HTTPException(429,{'code':'SHARE_COOLDOWN','message':'Take a moment before your next share.','retry_after':max(1,round(cooldown()-(time.time()-latest.created_at)))})
 db.add(ShareAction(id=str(data.share_action_id),user_id=u.id,destination_id=destination,channel=data.channel,outcome=data.outcome));db.flush()
 event(db,u,'share_action_counted',destination,data.channel);event(db,u,'share_progress_updated',destination,data.channel);event(db,u,'share_action_recorded',destination,data.channel);event(db,u,'world_unlock_progress',destination,data.channel)
 if not owned and progress(db,u,destination)>=SHARE_GOAL:
  db.add(WorldAccess(user_id=u.id,destination_id=destination,source='share'));db.flush();event(db,u,'world_unlocked_by_share',destination,data.channel);event(db,u,'world_unlocked',destination,data.channel)
 return {**state(db,u),'counted':True,'duplicate':False}

CLIENT_EVENTS={'all_destinations_viewed','destination_search','destination_previewed','destination_online_count_seen','locked_world_opened','share_channel_selected','world_entered_after_unlock'}
class Telemetry(Strict):
 kind:str=Field(max_length=50)
 destination_id:str=Field(default='',max_length=80)
 channel:str=Field(default='',max_length=20)
@router.post('/events',status_code=202)
def telemetry(data:Telemetry,u=Depends(current_user),db=Depends(get_db)):
 if data.kind not in CLIENT_EVENTS:raise HTTPException(422,'Unsupported event')
 if data.destination_id:check_city(data.destination_id)
 if data.channel and data.channel not in CHANNELS:raise HTTPException(422,'Unsupported channel')
 event(db,u,data.kind,data.destination_id,data.channel)
 if data.kind=='locked_world_opened':event(db,u,'locked_world_viewed',data.destination_id)
 return {'ok':True}
class Attribution(Strict):
 code:str=Field(max_length=40)
@router.post('/attribution',status_code=202)
def attribute(data:Attribution,u=Depends(current_user),db=Depends(get_db)):
 row=db.get(ShareInvite,data.code)
 if row and row.user_id!=u.id and u.created_at>time.time()-86400 and not db.scalar(select(GrowthEvent.id).where(GrowthEvent.user_id==u.id,GrowthEvent.kind=='invite_registration')):
  event(db,u,'invite_registration',row.destination_id,code=row.code)
 return {'ok':True}
@router.post('/invites/{code}/opened',status_code=202)
def opened(code:str,db=Depends(get_db)):
 row=db.get(ShareInvite,code)
 if not row:raise HTTPException(404,'Invite not found')
 # Anonymous aggregate only; no recipient ID, device fingerprint or IP is stored.
 db.add(GrowthEvent(kind='shared_invite_opened',destination_id=row.destination_id,invite_code=row.code));return {'ok':True}
@router.get('/metrics')
def metrics(u=Depends(require_admin),db=Depends(get_db)):
 by_kind=dict(db.execute(select(GrowthEvent.kind,func.count()).group_by(GrowthEvent.kind)).all())
 channels=dict(db.execute(select(ShareAction.channel,func.count()).group_by(ShareAction.channel)).all())
 by_world=dict(db.execute(select(ShareAction.destination_id,func.count()).group_by(ShareAction.destination_id)).all())
 unlocked=db.scalar(select(func.count()).select_from(WorldAccess).where(WorldAccess.source=='share')) or 0
 starts=db.execute(select(ShareAction.user_id,ShareAction.destination_id,func.min(ShareAction.created_at)).group_by(ShareAction.user_id,ShareAction.destination_id)).all()
 durations=[a.created_at-start for uid,d,start in starts if (a:=db.get(WorldAccess,(uid,d))) and a.source=='share']
 from .models import Presence,Session
 active=db.scalar(select(func.count()).select_from(Presence).join(User,User.id==Presence.user_id).where(Presence.updated_at>time.time()-45,User.suspended==False,Presence.user_id.in_(select(Session.user_id).where(Session.expires_at>time.time())))) or 0
 total=sum(channels.values())
 locked=dict(db.execute(select(GrowthEvent.destination_id,func.count()).where(GrowthEvent.kind=='locked_world_opened').group_by(GrowthEvent.destination_id)).all())
 return {'events':by_kind,'active_users_now':active,'total_share_actions':total,'lifetime_shares_per_current_active_user':total/active if active else None,'channel_rates':{k:v/total for k,v in channels.items()} if total else {},'locked_world_interest':locked,'registration_conversions':by_kind.get('invite_registration',0),'shares_by_channel':channels,'shares_by_world':by_world,'unlocks':unlocked,'destinations_started':len(starts),'unlock_completion_rate':unlocked/len(starts) if starts else 0,'mean_seconds_to_unlock':sum(durations)/len(durations) if durations else None,'notice':'Share actions are not verified posts or acquired users. Registration attribution is consent-based.'}
