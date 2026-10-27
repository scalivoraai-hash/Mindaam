"""Social events extend existing Event/Attendee and consent/media session records."""
import os,time
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import select,func
from .models import Event,Attendee,User,Presence,MediaSession,ConversationMember,Notification,Report
from .db import get_db
from .auth import current_user,display_profile
from .core import Strict,serialize,notify as base_notify,check_city,emit
from .world import blocked,friends
from . import conversations
router=APIRouter(prefix='/api/events')
def notify(db,uid,kind,body,source=''):
 from .talk import preferences
 if preferences(db,uid).get('event_notifications',True):base_notify(db,uid,kind,body,source)

TYPES=['Social Hangout','Public Talk','Discussion','Networking','Audio Room','Video Meetup','Community Meetup','Gaming / Activity','Concert','Movie Premiere','Film Festival','Screening','Creator Release','Other']

def attendance(db,e):return list(db.scalars(select(Attendee).where(Attendee.event_id==e.id,Attendee.state=='active')))
def host(db,e,u):
 a=db.get(Attendee,(e.id,u.id))
 return e.host_id==u.id or bool(a and a.state=='active' and a.role=='cohost')
def visible(db,e,u):
 a=db.get(Attendee,(e.id,u.id))
 return not blocked(db,u.id,e.host_id) and (e.visibility=='public' and e.status!='draft' or host(db,e,u) or a is not None or friends(db,u.id,e.host_id))
def get(db,id,u,moderator=False):
 e=db.scalar(select(Event).where(Event.id==id).with_for_update())
 if not e or not visible(db,e,u):raise HTTPException(404,'Event unavailable')
 if moderator and not host(db,e,u):raise HTTPException(403,'Only event hosts can do that')
 return e

def view(db,e,u,compact=False):
 a=db.get(Attendee,(e.id,u.id));people=attendance(db,e);moderator=host(db,e,u)
 from .event_presentation import state_view
 presentation=state_view(e,a,moderator)
 from .venue_rentals import booking
 reserved=booking(db,e.id) if not compact and e.venue_experience_type=='auditorium' else None
 from .event_tickets import summary
 from .event_engagement import summary as engagement
 programme={k:v for k,v in (e.programme or {}).items() if k not in ['polls','questions'] and (moderator or k!='rights_note') and (not compact or k in ['cover_image','arena_booking_required'])}
 return {**serialize(e),'server_time':time.time(),'organiser':{'id':e.host_id,'name':db.get(User,e.host_id).username},'programme':programme,'engagement':engagement(e,u.id,moderator) if not compact and (moderator or a and a.state=='active') else None,'ticketing':None if compact else summary(db,e,u),'presentation':presentation,'venue_booking':serialize(reserved) if reserved and moderator else ({'starts_at':reserved.starts_at,'ends_at':reserved.ends_at} if reserved else None),'joined':bool(a and a.state=='active'),'my_state':a.state if a else None,'my_role':a.role if a else None,'my_hand':bool(a and a.hand),'can_manage':moderator,'attendees':len(people),'speakers':sum(p.role in ['host','cohost','speaker'] for p in people),'participants':[{'id':p.user_id,'username':person.username,'avatar':person.avatar,'friend':friends(db,u.id,person.id),'role':p.role,'hand':p.hand,'share_state':p.share_state,**display_profile(person)} for p in people if (person:=db.get(User,p.user_id))] if moderator or a and a.state=='active' else [],'requests':[{'id':p.user_id,'username':db.get(User,p.user_id).username} for p in db.scalars(select(Attendee).where(Attendee.event_id==e.id,Attendee.state=='pending'))] if moderator else []}

class Programme(Strict):
 agenda:str=Field(default='',max_length=1500)
 cover_image:str=Field(default='',max_length=500,pattern=r'^(https://[^\s]+|/uploads/[^\s]+)?$')
 arena_booking_required:bool=False
 rights_confirmed:bool=False
 rights_note:str=Field(default='',max_length=500)

class EventInput(Strict):
 programme:Programme=Field(default_factory=Programme)
 ticket_price:int=Field(default=0,ge=0,le=1000000,strict=True)
 title:str=Field(min_length=3,max_length=120)
 description:str=Field(default='',max_length=1000)
 city:str
 starts_at:float=Field(allow_inf_nan=False)
 ends_at:float|None=Field(default=None,allow_inf_nan=False)
 capacity:int=Field(default=50,ge=2,le=250)
 event_type:Literal['Social Hangout','Public Talk','Discussion','Networking','Audio Room','Video Meetup','Community Meetup','Gaming / Activity','Concert','Movie Premiere','Film Festival','Screening','Creator Release','Other']='Social Hangout'
 communication_mode:Literal['text','voice','liveface']='text'
 visibility:Literal['public','private']='public'
 venue_experience_type:Literal['standard','auditorium']='standard'
 chat_enabled:bool=True
 status:Literal['draft','scheduled']='scheduled'

def validate(data,max_seconds=14400):
 check_city(data.city)
 if data.event_type in ['Movie Premiere','Film Festival','Screening','Creator Release'] and not data.programme.rights_confirmed:raise HTTPException(422,'Confirm your rights to screen this content')
 if data.starts_at<time.time()-60:raise HTTPException(422,'Choose a current or future start time')
 if data.ends_at and (data.ends_at<=data.starts_at or data.ends_at-data.starts_at>max_seconds):raise HTTPException(422,'Events can last up to four hours')
 if data.communication_mode!='text' and data.event_type!='Public Talk' and data.venue_experience_type!='auditorium' and data.capacity>conversations.rules()['max_participants']:raise HTTPException(422,'Small media meetups use the configured conversation limit; choose Public Talk for an audience')

@router.get('')
def listing(city:str|None=None,u=Depends(current_user),db=Depends(get_db)):
 q=select(Event).where(Event.status.in_(['draft','scheduled','live']),((Event.starts_at>time.time()-14400)|((Event.status=='live')&(Event.ends_at>time.time()))))
 if city:check_city(city);q=q.where(Event.city==city)
 return [view(db,e,u) for e in db.scalars(q.order_by(Event.starts_at).limit(100)) if visible(db,e,u)]
@router.post('',status_code=201)
def create(data:EventInput,u=Depends(current_user),db=Depends(get_db)):
 if not u.onboarded:raise HTTPException(409,'Complete your profile first')
 validate(data)
 data.programme.arena_booking_required=data.venue_experience_type=='auditorium'
 from .media_policy import settings
 limits=settings(db)
 if 'capacity' not in data.model_fields_set:data.capacity=limits['free_event_max_audience']
 if data.capacity>limits['event_capacity_limit']:raise HTTPException(422,'This event exceeds the current tested capacity')
 if db.scalar(select(func.count()).select_from(Event).where(Event.host_id==u.id,Event.created_at>time.time()-3600))>=5:raise HTTPException(429,'Please wait before creating more events')
 e=Event(**data.model_dump(),host_id=u.id);p=db.get(Presence,u.id)
 if p and p.city==data.city:e.x,e.z=p.x,p.z
 db.add(e);db.flush();db.add(Attendee(event_id=e.id,user_id=u.id,role='host'));db.flush();return view(db,e,u)
@router.get('/{id}')
def detail(id:str,u=Depends(current_user),db=Depends(get_db)):return view(db,get(db,id,u),u)
@router.put('/{id}')
def edit(id:str,data:EventInput,u=Depends(current_user),db=Depends(get_db)):
 e=get(db,id,u,True)
 if e.status not in ['draft','scheduled']:raise HTTPException(409,'Only upcoming events can be edited')
 from .venue_rentals import booking
 reserved=booking(db,id)
 if reserved and (data.city!=reserved.city or data.starts_at!=reserved.starts_at or data.ends_at!=reserved.ends_at or data.venue_experience_type!='auditorium'):raise HTTPException(409,'A reserved venue’s location and time cannot be changed')
 from .event_tickets import sales
 if sales(db,id) and (data.ticket_price!=e.ticket_price or data.starts_at!=e.starts_at or data.ends_at!=e.ends_at or data.status!=e.status or data.city!=e.city or data.visibility!=e.visibility or data.venue_experience_type!=e.venue_experience_type or data.capacity<sales(db,id)+1):raise HTTPException(409,'Sold tickets protect this event’s price, time, city and reserved audience capacity')
 if data.ticket_price!=e.ticket_price and len(attendance(db,e))>1:raise HTTPException(409,'Ticket prices cannot change after participants join')
 validate(data,86400 if reserved else 14400)
 from .media_policy import settings
 if data.capacity>settings(db)["event_capacity_limit"]:raise HTTPException(422,"This event exceeds the current tested capacity")
 if data.capacity<len(attendance(db,e)):raise HTTPException(409,'Capacity cannot be smaller than the joined group')
 data.programme.arena_booking_required=bool((e.programme or {}).get('arena_booking_required')) or (data.venue_experience_type=='auditorium' and e.venue_experience_type!='auditorium')
 payload=data.model_dump();payload['programme'].update({k:v for k,v in (e.programme or {}).items() if k in ['highlights','polls','questions']})
 for k,v in payload.items():setattr(e,k,v)
 return view(db,e,u)

def add_media(db,e,a):
 if not e.session_id:return
 m=db.get(ConversationMember,(e.session_id,a.user_id))
 if not m:m=ConversationMember(session_id=e.session_id,user_id=a.user_id);db.add(m)
 m.state='active';m.joined_at=time.time();m.left_at=None;m.reason=None;m.warning=False;m.role='ORIGINAL_MODERATOR' if a.role in ['host','cohost'] else 'JOINED_PARTICIPANT'

def eligible(db,e,u):
 if e.status not in ['scheduled','live']:raise HTTPException(409,'This event is not open')
 a=db.get(Attendee,(e.id,u.id))
 if a and a.state=='banned':raise HTTPException(403,'You have been removed from this event')
 if any(blocked(db,u.id,p.user_id) for p in attendance(db,e)):raise HTTPException(403,'Privacy settings prevent joining this event')
 from .media_policy import settings
 if len(attendance(db,e))>=min(e.capacity,settings(db)['event_capacity_limit']) and not (a and a.state=='active'):raise HTTPException(409,'Event is full')
 return a
@router.post('/{id}/join')
def join(id:str,u=Depends(current_user),db=Depends(get_db)):
 e=get(db,id,u);a=eligible(db,e,u)
 if a and a.state in ['active','pending']:return view(db,e,u)
 needs_approval=e.visibility=='private' and not host(db,e,u) and (not a or a.state!='approved')
 if not needs_approval:
  from .event_tickets import require_ticket
  require_ticket(db,e,u)
 if not a:a=Attendee(event_id=e.id,user_id=u.id);db.add(a)
 # Even invited private guests require approval by a host.
 a.state='pending' if needs_approval else 'active';a.joined_at=time.time();a.last_seen=time.time();a.role='audience' if e.event_type=='Public Talk' or e.venue_experience_type=='auditorium' else 'speaker'
 if a.state=='active':add_media(db,e,a)
 else:notify(db,e.host_id,'event.join_request',u.username+' would like to join '+e.title,e.id)
 db.flush();return view(db,e,u)

class InviteInput(Strict):
 user_id:str
@router.post('/{id}/invite')
def invite(id:str,data:InviteInput,u=Depends(current_user),db=Depends(get_db)):
 e=get(db,id,u,True);p=db.get(User,data.user_id)
 if not p or p.suspended or blocked(db,u.id,p.id):raise HTTPException(404,'Explorer unavailable')
 a=db.get(Attendee,(id,p.id))
 if a:return {'ok':True}
 db.add(Attendee(event_id=id,user_id=p.id,state='invited'))
 notify(db,p.id,'event.invited',u.username+' invited you to '+e.title,id);return {'ok':True}

def finish(db,e,status):
 if status=='cancelled':
  from .event_tickets import EventTicket
  affected=set(db.scalars(select(EventTicket.user_id).where(EventTicket.event_id==e.id)));affected.add(e.host_id)
  list(db.scalars(select(User).where(User.id.in_(affected)).order_by(User.id).with_for_update()))
  from .event_tickets import refund_cancelled
  refund_cancelled(db,e)
  from .venue_rentals import cancel_reservation
  cancel_reservation(db,e)
 e.status=status
 if e.session_id:
  s=db.get(MediaSession,e.session_id);s.state='ended';s.ended_at=time.time();s.end_reason='event_'+status
  for m in conversations.members(db,s):m.state='left';m.left_at=time.time();m.reason='event_'+status
 for a in db.scalars(select(Attendee).where(Attendee.event_id==e.id,Attendee.state.in_(['active','pending']))):
  notify(db,a.user_id,'event.'+status,e.title+' '+status,e.id);a.state='left';a.hand=False;a.share_state='none'
@router.post('/{id}/state/{action}')
def change_state(id:str,action:Literal['start','end','cancel'],u=Depends(current_user),db=Depends(get_db)):
 e=get(db,id,u,True)
 if action=='cancel' and e.status not in ['draft','scheduled','live','cancelled']:raise HTTPException(409,'This event has already ended')
 if action=='end' and e.status not in ['live','ended']:raise HTTPException(409,'Cancel an upcoming event so its tickets are refunded')
 if action=='start':
  if e.status=='live':return view(db,e,u)
  if e.status!='scheduled':raise HTTPException(409,'Schedule this event first')
  from .venue_rentals import start_gate
  start_gate(db,e)
  e.status='live';e.starts_at=time.time();e.ends_at=e.ends_at or time.time()+14400
  s=MediaSession(requester=e.host_id,target=e.host_id,kind=e.communication_mode,state='accepted',accepted_at=time.time(),event_id=e.id,join_policy='closed');db.add(s);db.flush();e.session_id=s.id
  for a in attendance(db,e):add_media(db,e,a)
  if e.venue_experience_type=='auditorium':
   p=db.get(Presence,u.id)
   if p and p.city==e.city and p.zone_id=='world':enter_venue(e.id,u,db)
 else:finish(db,e,'ended' if action=='end' else 'cancelled')
 db.flush();return view(db,e,u)

@router.post('/{id}/leave')
def leave(id:str,u=Depends(current_user),db=Depends(get_db)):
 e=get(db,id,u);a=db.get(Attendee,(id,u.id))
 if e.host_id==u.id:finish(db,e,'ended')
 elif a:
  a.state='cancelled' if a.state=='pending' else 'left';a.hand=False;a.share_state='none'
  if e.session_id:
   m=db.get(ConversationMember,(e.session_id,u.id))
   if m:conversations.end_member(db,db.get(MediaSession,e.session_id),m,'left')
 return {'ok':True}
@router.post('/{id}/hand')
def hand(id:str,u=Depends(current_user),db=Depends(get_db)):
 e=get(db,id,u);a=db.get(Attendee,(id,u.id))
 if not a or a.state!='active' or a.role!='audience' or e.status!='live':raise HTTPException(403,'Join the live audience first')
 a.hand=not a.hand;return {'raised':a.hand}

@router.post('/{id}/people/{user_id}/{action}')
async def moderate(id:str,user_id:str,action:Literal['approve','decline','decline_hand','remove','speaker','audience','cohost'],u=Depends(current_user),db=Depends(get_db)):
 from starlette.concurrency import run_in_threadpool
 from . import media
 def update():
  e=get(db,id,u,True);a=db.get(Attendee,(id,user_id))
  if not a:raise HTTPException(404,'Participant unavailable')
  if user_id==e.host_id:raise HTTPException(403,'The creator cannot be removed or demoted')
  if a.role=='cohost' and u.id!=e.host_id:raise HTTPException(403,'Only the creator can change a co-host')
  if action in ['approve','decline']:
   if a.state=='active' and action=='approve':return e.session_id
   if a.state!='pending':raise HTTPException(409,'Request already answered')
   if action=='approve':
    eligible(db,e,db.get(User,user_id))
    from .event_tickets import entitled
    a.state='active' if entitled(db,e,db.get(User,user_id)) else 'approved';a.joined_at=time.time()
    if a.state=='active':add_media(db,e,a)
   else:a.state='declined'
   notify(db,user_id,'event.join_'+action,e.title+(' — you are welcome to join' if action=='approve' else ' — request declined'),id)
  elif action=='decline_hand':
   if a.state!='active' or a.role!='audience':raise HTTPException(409,'No audience hand to decline')
   a.hand=False;notify(db,user_id,'event.hand_declined','The host has finished reviewing your stage request.',id)
  elif action=='remove':
   a.state='banned';a.hand=False;a.share_state='none'
   if e.session_id:
    m=db.get(ConversationMember,(e.session_id,user_id))
    if m:conversations.end_member(db,db.get(MediaSession,e.session_id),m,'removed')
  else:
   if a.state!='active' or e.status!='live':raise HTTPException(409,'Participant is not in the live event')
   if action=='cohost' and u.id!=e.host_id:raise HTTPException(403,'Only the creator can appoint co-hosts')
   from .media_policy import settings
   if action in ['speaker','cohost'] and a.role not in ['host','cohost','speaker'] and sum(p.role in ['host','cohost','speaker'] for p in attendance(db,e))>=settings(db)['auditorium_max_stage_video']:raise HTTPException(409,'The stage is full (host plus up to three guests)')
   a.role=action;a.hand=False;a.permission_dirty=True;a.permission_revision=(a.permission_revision or 0)+1
   p=db.get(Presence,user_id)
   if e.venue_experience_type=='auditorium' and p and p.zone_id=='event:'+id:
    from .civic import entry_position
    p.x,p.z=entry_position(db,p.zone_id,user_id,action in ['speaker','cohost']);p.last_move=time.time()
  db.flush();sid=e.session_id;db.commit();return sid
 sid=await run_in_threadpool(update)
 if sid:
  if action=='remove':await media.remove_participant(sid,user_id)
  elif action in ['speaker','audience','cohost']:
   from .event_presentation import reconcile_permission
   def reconcile_and_commit():
    reconcile_permission(db,id,user_id)
    # The flush/commit can wait on another transaction. Keep it in the same
    # worker as reconciliation so the ASGI loop can finish competing requests.
    db.commit()
   await run_in_threadpool(reconcile_and_commit)
 return {'ok':True}

class Announcement(Strict):
 body:str=Field(min_length=1,max_length=300)
@router.post('/{id}/announce')
def announce(id:str,data:Announcement,u=Depends(current_user),db=Depends(get_db)):
 e=get(db,id,u,True)
 for a in attendance(db,e):notify(db,a.user_id,'event.announcement',data.body,e.id)
 return {'ok':True}
@router.post('/{id}/report',status_code=201)
def report(id:str,data:Announcement,u=Depends(current_user),db=Depends(get_db)):
 e=get(db,id,u);db.add(Report(reporter_id=u.id,target_id=e.host_id,category='event',details=e.id+' '+e.title+' — '+data.body));return {'ok':True}

def maintenance(db):
 for e in db.scalars(select(Event).where(Event.status.in_(['scheduled','live'])).with_for_update()):
  from .event_presentation import expire
  expire(db,e)
  if not (creator:=db.get(User,e.host_id)) or creator.suspended:finish(db,e,'cancelled' if e.status=='scheduled' else 'ended');continue
  if e.status=='live' and e.ends_at and e.ends_at<time.time():finish(db,e,'ended')
  elif e.status=='scheduled' and not e.reminded and 0<e.starts_at-time.time()<300:
   from .event_tickets import EventTicket
   recipients={a.user_id for a in attendance(db,e)}|set(db.scalars(select(EventTicket.user_id).where(EventTicket.event_id==e.id,EventTicket.refunded_at==None)))
   for user_id in recipients:notify(db,user_id,'event.starting',e.title+' starts soon',e.id)
   e.reminded=True


def permission_jobs(db):
 from .event_presentation import effective_share
 return [(e.id,e.session_id,a.user_id,a.role,e.communication_mode,effective_share(e,a),a.permission_revision) for e in db.scalars(select(Event).where(Event.status=='live',Event.session_id!=None)) for a in attendance(db,e) if a.permission_dirty]

class ReactionInput(Strict):
 emoji:Literal['👏','❤️','🔥','😂']
@router.post('/{id}/react')
def react(id:str,data:ReactionInput,u=Depends(current_user),db=Depends(get_db)):
 from .models import Analytics
 e=get(db,id,u);a=db.get(Attendee,(id,u.id))
 if not a or a.state!='active' or e.status!='live':raise HTTPException(403,'Join the live event first')
 if db.scalar(select(func.count()).select_from(Analytics).where(Analytics.user_id==u.id,Analytics.kind=='event.reaction',Analytics.created_at>time.time()-10))>=4:raise HTTPException(429,'Give other reactions a moment')
 db.add(Analytics(user_id=u.id,kind='event.reaction',source=id+':'+data.emoji));return {'ok':True}
class GiftInput(Strict):
 id:str=Field(min_length=36,max_length=36)
 gift:Literal['rose','diamond','crown','rocket']
 expected_cost:int|None=Field(default=None,ge=1,le=1000)
@router.post('/{id}/gift')
def gift(id:str,data:GiftInput,u=Depends(current_user),db=Depends(get_db)):
 from uuid import UUID
 from .economy import credit,balance,config
 try:UUID(data.id)
 except ValueError:raise HTTPException(422,'Invalid gift ID')
 e=get(db,id,u);a=db.get(Attendee,(id,u.id))
 if not a or a.state!='active' or e.status!='live':raise HTTPException(403,'Join the live event first')
 prices=config(db,'event_gifts',{'rose':1,'diamond':5,'crown':20,'rocket':50});cost=prices.get(data.gift)
 if not isinstance(cost,int) or not 1<=cost<=1000:raise HTTPException(409,'Gift currently unavailable')
 from .models import Ledger
 prior=db.scalar(select(Ledger).where(Ledger.user_id==u.id,Ledger.currency=='credits',Ledger.idempotency_key=='event-gift:'+data.id))
 if prior:
  if prior.kind!='event_gift' or prior.source!=id+':'+data.gift:raise HTTPException(409,'Gift ID already used')
  return {'id':prior.id,'balance':balance(db,u.id),'gift':data.gift,'cost':-prior.amount}
 if data.expected_cost!=cost:raise HTTPException(409,'The gift price changed. Close the confirmation and choose your gift again.')
 tx=credit(db,u.id,-cost,'event_gift',id+':'+data.gift,'event-gift:'+data.id)
 return {'id':tx.id,'balance':balance(db,u.id),'gift':data.gift,'cost':cost}
@router.get('/{id}/activity')
def event_activity(id:str,u=Depends(current_user),db=Depends(get_db)):
 from .models import Analytics,Ledger
 from .economy import config
 e=get(db,id,u);a=db.get(Attendee,(id,u.id))
 if not a or a.state!='active':raise HTTPException(403,'Join this event first')
 a.last_seen=time.time()
 return {'reactions':[{'emoji':r.source.split(':')[-1],'at':r.created_at} for r in db.scalars(select(Analytics).where(Analytics.kind=='event.reaction',Analytics.source.like(id+':%'),Analytics.created_at>time.time()-8).limit(30))],'gifts':[{'gift':g.source.split(':')[-1],'at':g.created_at} for g in db.scalars(select(Ledger).where(Ledger.kind=='event_gift',Ledger.source.like(id+':%'),Ledger.created_at>time.time()-15).limit(20))],'gift_prices':config(db,'event_gifts',{'rose':1,'diamond':5,'crown':20,'rocket':50})}
@router.post('/{id}/venue/enter')
def enter_venue(id:str,u=Depends(current_user),db=Depends(get_db)):
 from .growth import require_access
 e=get(db,id,u);a=db.get(Attendee,(id,u.id));p=db.get(Presence,u.id)
 if e.venue_experience_type!='auditorium' or e.status!='live' or not a or a.state!='active':raise HTTPException(403,'Join the live auditorium first')
 from .event_tickets import require_ticket
 require_ticket(db,e,u)
 require_access(db,u,e.city)
 from .mobility import current
 if current(db,u):raise HTTPException(409,'Exit your rental first')
 if not p or p.city!=e.city or p.zone_id not in ['world','event:'+id]:raise HTTPException(409,'Enter this world and exit any vehicle or building first')
 if p.zone_id=='world':
  from .civic import entry_position
  p.return_position={'x':p.x,'z':p.z};p.x,p.z=entry_position(db,'event:'+id,u.id,a.role in ['host','cohost','speaker'])
 p.zone_id='event:'+id
 p.mode='walk';p.updated_at=time.time();p.last_move=time.time();return {'ok':True}
@router.post('/{id}/venue/exit')
def exit_venue(id:str,u=Depends(current_user),db=Depends(get_db)):
 from .geography import safe_spawn,traversable
 p=db.get(Presence,u.id)
 if p and p.zone_id=='event:'+id:
  x,z=p.return_position.get('x',0),p.return_position.get('z',0);p.x,p.z=(x,z) if traversable(p.city,x,z) else safe_spawn(p.city);p.zone_id='world';p.return_position={};p.last_move=time.time();p.updated_at=time.time()
 return {'ok':True}
def auditorium_scene(db,p,u):
 if not p.zone_id.startswith('event:'):return None
 e=db.get(Event,p.zone_id[6:]);a=db.get(Attendee,(e.id,u.id)) if e else None
 if not e or e.status!='live' or not a or a.state!='active':
  exit_venue(p.zone_id[6:],u,db);return None
 from .civic import scene
 return {'id':e.id,'name':e.title,'template':'auditorium','notice':'Mindaam Live Auditorium','event':view(db,e,u,compact=True),'geography':{'city':p.city,'radius':40,'spawn':[0,8],'features':[]}}

class ChatSetting(Strict):
 enabled:bool
@router.put('/{id}/chat')
def chat_setting(id:str,data:ChatSetting,u=Depends(current_user),db=Depends(get_db)):
 e=get(db,id,u,True);e.chat_enabled=data.enabled;return {'enabled':e.chat_enabled}
