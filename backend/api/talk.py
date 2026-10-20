"""Consent-gated private conversations delivered on the world WebSocket."""
import time,math,os
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import Column,String,Float,JSON,ForeignKey,select,or_,and_,func
from .db import Base,get_db
from .models import User,Presence,MediaSession,Social,ConversationMember,ConversationJoin
from . import conversations as conversations
from .auth import current_user,display_profile
from .core import Strict,serialize,emit,notify
from .world import blocked,friends,visible
router=APIRouter(prefix='/api/talk')
DEFAULTS={'text':'nearby','voice':'nearby','liveface':'nearby','event_notifications':True}
def rules():
 return {'interaction_metres':float(os.getenv('TALK_INTERACTION_METRES','10')), 'quick_metres':float(os.getenv('TALK_QUICK_METRES','5')), 'request_seconds':int(os.getenv('TALK_REQUEST_SECONDS','30')), 'cooldown_seconds':int(os.getenv('TALK_COOLDOWN_SECONDS','30')),**conversations.rules()}
@router.get('/config')
def talk_config():return rules()
class TalkPreference(Base):
 __tablename__='talk_preferences'
 user_id=Column(ForeignKey('users.id'),primary_key=True)
 settings=Column(JSON,nullable=False,default=dict)
class TalkMessage(Base):
 __tablename__='talk_messages'
 id=Column(String(36),primary_key=True)
 session_id=Column(ForeignKey('media_sessions.id'),nullable=False,index=True)
 sender=Column(ForeignKey('users.id'),nullable=False)
 body=Column(String(2000),nullable=False)
 created_at=Column(Float,nullable=False,default=time.time)
class TalkCursor(Base):
 __tablename__='talk_cursors'
 session_id=Column(ForeignKey('media_sessions.id'),primary_key=True)
 user_id=Column(ForeignKey('users.id'),primary_key=True)
 read_at=Column(Float,nullable=False,default=0)
 typing_until=Column(Float,nullable=False,default=0)
def preferences(db,id):
 p=db.get(TalkPreference,id);return {**DEFAULTS,**(p.settings if p else {})}
def nearby(db,u,target):
 a,b=db.get(Presence,u.id),db.get(Presence,target.id)
 return bool(a and b and a.city==b.city and a.zone_id==b.zone_id and min(a.updated_at,b.updated_at)>time.time()-45 and math.hypot(a.x-b.x,a.z-b.z)<=rules()['interaction_metres'] and visible(db,u,target,b,a) and visible(db,target,u,a,b))
def allowed(db,u,target,kind):
 if not target or target.suspended or u.id==target.id or blocked(db,u.id,target.id):return False
 if db.scalar(select(Social.id).where(Social.actor==target.id,Social.target==u.id,Social.kind=='mute')):return False
 policy=preferences(db,target.id)[kind]
 return (policy=='everyone' and (nearby(db,u,target) or friends(db,u.id,target.id))) or (policy=='connections' and friends(db,u.id,target.id)) or (policy=='following' and (friends(db,u.id,target.id) or bool(db.scalar(select(Social.id).where(Social.actor==target.id,Social.target==u.id,Social.kind=='follow'))))) or (policy=='nearby' and (nearby(db,u,target) or friends(db,u.id,target.id)))
class Preferences(Strict):
 event_notifications:bool=True
 text:Literal['everyone','nearby','connections','following','nobody']='nearby'
 voice:Literal['everyone','nearby','connections','following','nobody']='nearby'
 liveface:Literal['everyone','nearby','connections','following','nobody']='nearby'
@router.get('/preferences')
def get_preferences(u=Depends(current_user),db=Depends(get_db)):return preferences(db,u.id)
@router.put('/preferences')
def save_preferences(data:Preferences,u=Depends(current_user),db=Depends(get_db)):
 p=db.get(TalkPreference,u.id)
 if not p:p=TalkPreference(user_id=u.id);db.add(p)
 p.settings=data.model_dump();return p.settings
class Invitation(Strict):
 target_id:str
 kind:Literal['text','voice','liveface']='text'
@router.post('/request')
def request(data:Invitation,u=Depends(current_user),db=Depends(get_db)):
 list(db.scalars(select(User).where(User.id.in_([u.id,data.target_id])).order_by(User.id).with_for_update()))
 target=db.get(User,data.target_id)
 if not allowed(db,u,target,data.kind):raise HTTPException(403,'This person is not available for this request')
 if data.kind=='text':
  mine=select(ConversationMember.session_id).where(ConversationMember.user_id==u.id,ConversationMember.state=='active')
  theirs=select(ConversationMember.session_id).where(ConversationMember.user_id==target.id,ConversationMember.state=='active')
  connected=db.scalar(select(MediaSession).where(MediaSession.id.in_(mine),MediaSession.id.in_(theirs),MediaSession.state=='accepted',MediaSession.conversation_id==None,MediaSession.event_id==None).order_by(MediaSession.created_at.desc()).limit(1))
  if connected:
   conversations.enforce(db,connected)
   own=conversations.member(db,connected,u.id);peer=conversations.member(db,connected,target.id)
   if connected.state=='accepted' and own and own.state=='active' and peer and peer.state=='active':return serialize(connected)
 pair=or_(and_(MediaSession.requester==u.id,MediaSession.target==target.id),and_(MediaSession.requester==target.id,MediaSession.target==u.id))
 old=db.scalar(select(MediaSession).where(pair,MediaSession.kind==data.kind).order_by(MediaSession.created_at.desc()).limit(1));now=time.time()
 if old and old.state in ['pending','accepted'] and old.created_at>now-(rules()['request_seconds'] if old.state=='pending' else (86400 if data.kind=='text' else 600)):return serialize(old)
 if old and max(old.created_at,old.ended_at or 0)>now-rules()['cooldown_seconds']:raise HTTPException(429,'Please wait before requesting again')
 if db.scalar(select(func.count()).select_from(MediaSession).where(MediaSession.requester==u.id,MediaSession.created_at>now-60))>=8:raise HTTPException(429,'Too many invitations; wait a minute')
 parent=db.scalar(select(MediaSession).where(pair,MediaSession.kind=='text',MediaSession.state=='accepted').order_by(MediaSession.created_at.desc()).limit(1)) if data.kind!='text' else None
 s=MediaSession(requester=u.id,target=target.id,kind=data.kind,conversation_id=parent.id if parent else None,distance_policy='friends' if friends(db,u.id,target.id) else 'proximity',max_participants=parent.max_participants if parent else min(6,conversations.rules()['max_participants']));db.add(s);db.flush();emit(db,u,'talk_request_sent',s.id);notify(db,target.id,'interaction.requested',u.username+' wants to talk',s.id);return serialize(s)
def member(db,u,id,accepted=False):
 s=db.scalar(select(MediaSession).where(MediaSession.id==id).with_for_update())
 if not s:raise HTTPException(403,'Conversation unavailable')
 if accepted:conversations.enforce(db,s)
 own=conversations.member(db,s,u.id)
 if u.id not in [s.requester,s.target] and not own:raise HTTPException(403,'Conversation unavailable')
 if own and own.state!='active' and accepted:raise HTTPException(403,'You are no longer in this conversation')
 if any(blocked(db,u.id,m.user_id) for m in conversations.members(db,s) if m.user_id!=u.id):raise HTTPException(403,'Conversation unavailable')
 if accepted and (s.state!='accepted' or s.created_at<time.time()-86400):raise HTTPException(409,'Accept the conversation first')
 return s
class MessageInput(Strict):
 id:str=Field(min_length=36,max_length=36)
 body:str=Field(min_length=1,max_length=2000)
@router.post('/{id}/messages',status_code=201)
def send(id:str,data:MessageInput,u=Depends(current_user),db=Depends(get_db)):
 s=member(db,u,id,True)
 if s.event_id:
  from .models import Event
  if not db.get(Event,s.event_id).chat_enabled:raise HTTPException(403,'Event chat is switched off by the host')
 peers=[m.user_id for m in conversations.members(db,s) if m.user_id!=u.id]
 if any(preferences(db,peer)['text']=='nobody' or db.scalar(select(Social.id).where(Social.actor==peer,Social.target==u.id,Social.kind=='mute')) for peer in peers):raise HTTPException(403,'Messaging disabled')
 old=db.get(TalkMessage,data.id)
 if old:
  if old.sender!=u.id or old.session_id!=id or old.body!=data.body.strip():raise HTTPException(409,'Message ID already used')
  return serialize(old)
 if not data.body.strip():raise HTTPException(422,'Message is empty')
 if db.scalar(select(func.count()).select_from(TalkMessage).where(TalkMessage.sender==u.id,TalkMessage.created_at>time.time()-10))>=15:raise HTTPException(429,'Slow down')
 m=TalkMessage(id=data.id,session_id=id,sender=u.id,body=data.body.strip());db.add(m);db.flush();return serialize(m)
class Cursor(Strict):
 typing:bool=False
 read:bool=False
@router.put('/{id}/cursor')
def cursor(id:str,data:Cursor,u=Depends(current_user),db=Depends(get_db)):
 member(db,u,id,True);c=db.get(TalkCursor,(id,u.id))
 if not c:c=TalkCursor(session_id=id,user_id=u.id);db.add(c)
 if data.read:c.read_at=time.time()
 c.typing_until=time.time()+4 if data.typing else 0
 return {'ok':True}
def snapshot(db,u):
 now=time.time();own_ids=select(ConversationMember.session_id).where(ConversationMember.user_id==u.id)
 rows=db.scalars(select(MediaSession).where(or_(MediaSession.requester==u.id,MediaSession.target==u.id,MediaSession.id.in_(own_ids)),MediaSession.created_at>now-86400).order_by(MediaSession.created_at.desc()).limit(30)).all();result=[]
 for s in rows:
  active=conversations.members(db,s);own=conversations.member(db,s,u.id)
  peers=[m.user_id for m in active if m.user_id!=u.id]
  peer=db.get(User,peers[0] if peers else s.target if s.requester==u.id else s.requester)
  if not peer or peer.suspended or blocked(db,u.id,peer.id):continue
  if s.state=='pending' and s.created_at<now-rules()['request_seconds']:s.state='expired';s.ended_at=now;emit(db,u,'talk_request_expired',s.id)
  if s.state not in ['pending','accepted'] and (s.ended_at or s.created_at)<now-60:continue
  if own and own.state=='left' and (own.left_at or 0)<now-60:continue
  d={**conversations.view(db,s,u),'expires_at':s.created_at+rules()['request_seconds'],'peer':{'id':peer.id,'username':peer.username,'avatar':peer.avatar,**display_profile(peer)}}
  if d['state']=='accepted' and not s.conversation_id:
   cursors=[db.get(TalkCursor,(s.id,id)) for id in peers];own_cursor=db.get(TalkCursor,(s.id,u.id))
   msgs=list(db.scalars(select(TalkMessage).where(TalkMessage.session_id==s.id).order_by(TalkMessage.created_at.desc()).limit(50)))
   d['messages']=[{**serialize(m),'sender_name':(db.get(User,m.sender).username if db.get(User,m.sender) else 'Explorer'),'delivered':True,'read':bool(cursors and all(c and c.read_at>=m.created_at for c in cursors))} for m in reversed(msgs)];d['typing']=any(c and c.typing_until>now for c in cursors);d['unread']=sum(m.sender!=u.id and m.created_at>(own_cursor.read_at if own_cursor else 0) for m in msgs)
   joins=list(db.scalars(select(ConversationJoin).where(ConversationJoin.session_id==s.id,ConversationJoin.state=='pending')))
   for j in joins:
    if j.created_at<now-rules()['request_seconds']:j.state='expired'
   d['join_requests']=[{'user_id':j.user_id,'username':db.get(User,j.user_id).username,'state':j.state,**display_profile(db.get(User,j.user_id))} for j in joins if j.state=='pending' and u.id in [s.requester,s.target]]
  result.append(d)
 return result
@router.get('/state')
def state(u=Depends(current_user),db=Depends(get_db)):return snapshot(db,u)
@router.get('/nearby-conversations')
def nearby_groups(u=Depends(current_user),db=Depends(get_db)):
 return conversations.nearby_conversations(db,u)

@router.post('/conversation/{id}/join')
def ask_join(id:str,u=Depends(current_user),db=Depends(get_db)):
 s=db.scalar(select(MediaSession).where(MediaSession.id==id).with_for_update())
 if not s or s.conversation_id:raise HTTPException(403,'Conversation is not available to join')
 j=db.get(ConversationJoin,(id,u.id));now=time.time()
 own=conversations.member(db,s,u.id)
 if j and j.state=='accepted' and own and own.state=='active':return serialize(j)
 if not conversations.eligible(db,s,u):raise HTTPException(403,'Conversation is not available to join')
 if j and j.state=='pending' and j.created_at>now-rules()['request_seconds']:return serialize(j)
 if j and j.state=='accepted' and conversations.member(db,s,u.id) and conversations.member(db,s,u.id).state=='active':return serialize(j)
 if j and j.created_at>now-rules()['cooldown_seconds']:raise HTTPException(429,'Please wait before asking again')
 if not j:j=ConversationJoin(session_id=id,user_id=u.id);db.add(j)
 j.state='pending';j.created_at=now;j.decided_by=None;db.flush();return serialize(j)

@router.post('/conversation/{id}/join/{user_id}/{decision}')
def decide_join(id:str,user_id:str,decision:Literal['accept','reject','cancel'],u=Depends(current_user),db=Depends(get_db)):
 s=db.scalar(select(MediaSession).where(MediaSession.id==id).with_for_update());j=db.get(ConversationJoin,(id,user_id))
 if not s or not j:raise HTTPException(404,'Join request unavailable')
 own=conversations.member(db,s,u.id)
 if decision=='cancel':
  if u.id!=user_id:raise HTTPException(403,'Only the requester can cancel')
 elif not own or own.state!='active' or (conversations.rules()['approval_policy']=='host' and u.id!=s.requester) or (decision!='cancel' and conversations.rules()['approval_policy']=='originals' and u.id not in [s.requester,s.target]):raise HTTPException(403,'Only an authorised member can respond')
 if j.state=='accepted' and decision=='accept':return serialize(j)
 if j.state!='pending' or j.created_at<time.time()-rules()['request_seconds']:raise HTTPException(409,'Join request expired or already answered')
 if decision=='accept':
  person=db.get(User,user_id)
  if not person or not conversations.eligible(db,s,person):raise HTTPException(403,'Privacy, distance or capacity changed')
  for item in conversations.family(db,s):
   if item.state!='accepted':continue
   m=conversations.member(db,item,user_id)
   if not m:m=ConversationMember(session_id=item.id,user_id=user_id);db.add(m)
   m.state='active';m.role='JOINED_PARTICIPANT';m.joined_at=time.time();m.left_at=None;m.reason=None;m.out_since=None;m.warning=False
  j.state='accepted';j.decided_by=u.id
 else:j.state='cancelled' if decision=='cancel' else 'declined';j.decided_by=u.id
 db.flush();return serialize(j)

@router.post('/conversation/{id}/members/{user_id}/remove')
def remove_member(id:str,user_id:str,u=Depends(current_user),db=Depends(get_db)):
 s=member(db,u,id,True);s=conversations.root(db,s)
 if u.id not in [s.requester,s.target] or not conversations.member(db,s,u.id) or conversations.member(db,s,u.id).state!='active':raise HTTPException(403,'Only an original moderator can remove participants')
 if user_id in [s.requester,s.target]:raise HTTPException(403,'Original moderators cannot remove each other')
 target=conversations.member(db,s,user_id)
 if not target:raise HTTPException(404,'Participant unavailable')
 for item in conversations.family(db,s):
  own=conversations.member(db,item,user_id)
  if own:
   own.rejoin_after=time.time()+conversations.rules()['rejoin_cooldown']
   conversations.end_member(db,item,own,'removed')
 emit(db,u,'conversation.participant_removed',user_id)
 return {'ok':True,'rejoin_after':target.rejoin_after}

class JoinPolicy(Strict):
 policy:Literal['closed','friends','invite','approval']='approval'
@router.put('/conversation/{id}/policy')
def join_policy(id:str,data:JoinPolicy,u=Depends(current_user),db=Depends(get_db)):
 s=member(db,u,id,True)
 if u.id not in [s.requester,s.target]:raise HTTPException(403,'Only an original moderator can change joining')
 s.join_policy=data.policy;return {'policy':s.join_policy}

@router.post('/conversation/{id}/media/{kind}')
def group_media(id:str,kind:Literal['voice','liveface'],u=Depends(current_user),db=Depends(get_db)):
 s=member(db,u,id,True);s=conversations.root(db,s);active=conversations.members(db,s)
 if s.kind==kind:return conversations.view(db,s,u)
 old=db.scalar(select(MediaSession).where(MediaSession.conversation_id==s.id,MediaSession.kind==kind,MediaSession.state=='accepted').order_by(MediaSession.created_at.desc()))
 if old:
  own=conversations.member(db,old,u.id)
  if not own or own.state=='left':raise HTTPException(403,'Media consent is no longer active')
  return conversations.view(db,old,u)
 peers=[m for m in active if m.user_id!=u.id]
 if not peers:raise HTTPException(409,'Another member is required')
 if any(preferences(db,m.user_id)[kind]=='nobody' for m in peers):raise HTTPException(403,'A participant does not accept media requests')
 call=MediaSession(requester=u.id,target=peers[0].user_id,kind=kind,state='accepted',accepted_at=time.time(),conversation_id=s.id,distance_policy=s.distance_policy,max_participants=s.max_participants);db.add(call);db.flush()
 for m in active:db.add(ConversationMember(session_id=call.id,user_id=m.user_id,state='active' if m.user_id==u.id else 'invited',warning=False))
 db.flush();return conversations.view(db,call,u)

@router.post('/{id}/{action}')
def action(id:str,action:Literal['accept','reject','cancel','end'],u=Depends(current_user),db=Depends(get_db)):
 s=member(db,u,id)
 if action=='cancel':
  if u.id!=s.requester:raise HTTPException(403,'Only the sender may cancel')
  if s.state!='pending':raise HTTPException(409,'Invitation cannot be cancelled')
  s.state='cancelled';s.ended_at=time.time()
 elif action=='end':
  if s.event_id:
   from .events import leave
   return leave(s.event_id,u,db)
  if s.kind!='text':raise HTTPException(409,'Use the media end endpoint to disconnect both participants')
  conversations.leave(db,s,u.id,'left')
 else:
  if u.id!=s.target:raise HTTPException(403,'Only the recipient may respond')
  if s.state!='pending' or s.created_at<time.time()-rules()['request_seconds']:raise HTTPException(409,'Request expired or already answered')
  if action=='accept' and not allowed(db,db.get(User,s.requester),u,s.kind):raise HTTPException(403,'Privacy or proximity changed')
  s.state='accepted' if action=='accept' else 'rejected';s.accepted_at=time.time() if action=='accept' else None
  if action=='reject':s.ended_at=time.time()
 if action=='accept':conversations.members(db,s)
 emit(db,u,{'accept':'talk_request_accepted','reject':'talk_request_declined','cancel':'talk_request_cancelled','end':'talk_session_ended'}[action],s.id)
 return serialize(s)

class CapacityInput(Strict):
 maximum:int=Field(ge=2,le=10)
@router.put('/conversation/{id}/capacity')
def capacity(id:str,data:CapacityInput,u=Depends(current_user),db=Depends(get_db)):
 s=conversations.root(db,member(db,u,id,True))
 if s.event_id or u.id not in [s.requester,s.target]:raise HTTPException(403,'Only an original moderator may change conversation capacity')
 if data.maximum>conversations.rules()['max_participants']:raise HTTPException(422,'Above the platform maximum')
 if data.maximum<len(conversations.members(db,s)):raise HTTPException(409,'Cannot remove participants by reducing capacity')
 for item in conversations.family(db,s):item.max_participants=data.maximum
 emit(db,u,'conversation.capacity_changed',s.id)
 return {'capacity':data.maximum}
