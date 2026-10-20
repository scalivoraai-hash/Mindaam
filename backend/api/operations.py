"""Restricted platform operations and advertising. No arbitrary infrastructure access."""
import os,time,base64,hashlib,struct
from uuid import UUID
from typing import Literal
from urllib.parse import urlparse
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from pydantic import Field
from sqlalchemy import String,Float,Integer,Boolean,LargeBinary,ForeignKey,select,func,delete
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base,get_db
from .models import User,Session,Presence,Audit,Config,Ledger,Event,Attendee,MediaSession,Analytics,uid
from .auth import current_user,public_user,hash_password
from .core import Strict,serialize
router=APIRouter(prefix='/api')
class AdBoard(Base):
 __tablename__='ad_boards'
 id:Mapped[str]=mapped_column(String(100),primary_key=True)
 city:Mapped[str]=mapped_column(String(50),index=True)
 name:Mapped[str]=mapped_column(String(120))
 x:Mapped[float]=mapped_column(Float)
 z:Mapped[float]=mapped_column(Float)
 enabled:Mapped[bool]=mapped_column(Boolean,default=True)
class Creative(Base):
 __tablename__='ad_creatives'
 id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
 data:Mapped[bytes]=mapped_column(LargeBinary)
 mime:Mapped[str]=mapped_column(String(40))
 created_at:Mapped[float]=mapped_column(Float,default=time.time)
class AdCampaign(Base):
 __tablename__='ad_campaigns'
 id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
 advertiser:Mapped[str]=mapped_column(String(160))
 name:Mapped[str]=mapped_column(String(120))
 headline:Mapped[str]=mapped_column(String(180))
 creative_id:Mapped[str|None]=mapped_column(ForeignKey('ad_creatives.id'),nullable=True)
 board_id:Mapped[str]=mapped_column(ForeignKey('ad_boards.id'),index=True)
 starts_at:Mapped[float]=mapped_column(Float)
 ends_at:Mapped[float]=mapped_column(Float)
 cta_text:Mapped[str]=mapped_column(String(50),default='Learn more')
 cta_url:Mapped[str]=mapped_column(String(1000),default='')
 priority:Mapped[int]=mapped_column(Integer,default=0)
 status:Mapped[str]=mapped_column(String(20),default='draft')
 created_at:Mapped[float]=mapped_column(Float,default=time.time)
class AdEnquiry(Base):
 __tablename__='advertising_interest_requests'
 id:Mapped[str]=mapped_column(String(36),primary_key=True)
 user_id:Mapped[str|None]=mapped_column(ForeignKey('users.id'),index=True,nullable=True)
 business_name:Mapped[str]=mapped_column(String(160))
 contact_name:Mapped[str]=mapped_column(String(120))
 email:Mapped[str]=mapped_column(String(254))
 phone:Mapped[str]=mapped_column(String(60),default='')
 website:Mapped[str]=mapped_column(String(1000),default='')
 destination_id:Mapped[str]=mapped_column(String(50))
 board_id:Mapped[str]=mapped_column(ForeignKey('ad_boards.id'))
 campaign_dates:Mapped[str]=mapped_column(String(120),default='')
 message:Mapped[str]=mapped_column(String(3000),default='')
 status:Mapped[str]=mapped_column(String(20),default='NEW')
 created_at:Mapped[float]=mapped_column(Float,default=time.time)
class AdInteraction(Base):
 __tablename__='ad_interactions'
 id:Mapped[str]=mapped_column(String(64),primary_key=True)
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
 board_id:Mapped[str]=mapped_column(ForeignKey('ad_boards.id'),index=True)
 campaign_id:Mapped[str]=mapped_column(ForeignKey('ad_campaigns.id'),index=True)
 kind:Mapped[str]=mapped_column(String(20))
 created_at:Mapped[float]=mapped_column(Float,default=time.time)
class UserActivity(Base):
 __tablename__='user_activity_days'
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
 day:Mapped[int]=mapped_column(Integer,primary_key=True)
 last_seen:Mapped[float]=mapped_column(Float)
class OnlineSample(Base):
 __tablename__='online_samples'
 bucket:Mapped[int]=mapped_column(Integer,primary_key=True)
 city:Mapped[str]=mapped_column(String(50),primary_key=True)
 count:Mapped[int]=mapped_column(Integer)

def super_admin(u=Depends(current_user)):
 if u.role!='super_admin':raise HTTPException(403,'Super Admin access required')
 if u.must_change_password:raise HTTPException(403,'Change your initial password in Account Settings, then sign in again')
 return u

def audit(db,u,action,target,details=None):db.add(Audit(actor_id=u.id,action=action,target=target,details=details or {}))
def url(value):
 if value and (urlparse(value).scheme!='https' or not urlparse(value).netloc or urlparse(value).username):raise HTTPException(422,'Use a public HTTPS link')
 return value

def seed_inventory(db):
 from .locations import CITIES
 from .transit import hub
 for city in CITIES:
  id=city['id']+'-central-01'
  if not db.get(AdBoard,id):
   try:h=hub(city['id'])
   except HTTPException:continue
   db.add(AdBoard(id=id,city=city['id'],name=city['name']+' Central',x=h['x'],z=h['z']))

def active_campaign(db,id):return db.scalar(select(AdCampaign).where(AdCampaign.board_id==id,AdCampaign.status=='active',AdCampaign.starts_at<=time.time(),AdCampaign.ends_at>time.time()).order_by(AdCampaign.priority.desc(),AdCampaign.created_at.desc()).limit(1))
def boards(db,city):
 result=[]
 for b in db.scalars(select(AdBoard).where(AdBoard.city==city,AdBoard.enabled==True)):
  c=active_campaign(db,b.id)
  result.append({**serialize(b),'campaign':{**serialize(c),'creative_mime':db.get(Creative,c.creative_id).mime if c.creative_id else None,'creative_url':'/api/ads/creatives/'+c.creative_id if c.creative_id else None} if c else None})
 return result
@router.get('/ads/boards/{city}')
def board_list(city:str,db=Depends(get_db)):return boards(db,city)
@router.get('/ads/creatives/{id}')
def creative(id:str,db=Depends(get_db)):
 c=db.get(Creative,id)
 if not c:raise HTTPException(404,'Creative unavailable')
 return Response(c.data,media_type=c.mime,headers={'Cache-Control':'public, max-age=86400, immutable','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'"})
class EnquiryInput(Strict):
 id:UUID
 business_name:str=Field(min_length=2,max_length=160)
 contact_name:str=Field(min_length=2,max_length=120)
 email:str=Field(min_length=5,max_length=254,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
 phone:str=Field(default='',max_length=60)
 website:str=Field(default='',max_length=1000)
 destination_id:str=Field(max_length=50)
 board_id:str=Field(max_length=100)
 campaign_dates:str=Field(default='',max_length=120)
 message:str=Field(default='',max_length=3000)
 consent:bool
@router.post('/ads/enquiries',status_code=201)
def enquiry(data:EnquiryInput,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update());old=db.get(AdEnquiry,str(data.id))
 if old:
  if old.user_id!=u.id:raise HTTPException(409,'Submission ID conflict')
  return {'id':old.id,'status':old.status}
 if not data.consent:raise HTTPException(422,'Contact consent is required')
 b=db.get(AdBoard,data.board_id)
 if not b or b.city!=data.destination_id:raise HTTPException(422,'Select an available advertising board')
 if db.scalar(select(func.count()).select_from(AdEnquiry).where(AdEnquiry.user_id==u.id,AdEnquiry.created_at>time.time()-3600))>=3:raise HTTPException(429,'Your enquiries are saved. Please wait before submitting another.')
 url(data.website);values=data.model_dump(exclude={'id','consent'});e=AdEnquiry(id=str(data.id),user_id=u.id,**values);db.add(e);audit(db,u,'advertising.enquiry',e.id,{'contact_consent':True});return {'id':e.id,'status':'NEW'}
class InteractionInput(Strict):
 kind:Literal['impression','click']
 campaign_id:str
@router.post('/ads/boards/{id}/interaction')
def interaction(id:str,data:InteractionInput,u=Depends(current_user),db=Depends(get_db)):
 if not u.analytics_consent:return {'ok':True,'counted':False}
 b=db.get(AdBoard,id);p=db.get(Presence,u.id);c=active_campaign(db,id)
 if not b or not p or p.city!=b.city or p.zone_id!='world' or not c or c.id!=data.campaign_id:raise HTTPException(409,'Advertisement is not visible in this world')
 import math
 if math.hypot(p.x-b.x,p.z-b.z)>100:raise HTTPException(409,'Approach this board first')
 key=hashlib.sha256(f'{u.id}:{id}:{c.id}:{data.kind}:{int(time.time()/60)}'.encode()).hexdigest()
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 if not db.get(AdInteraction,key):db.add(AdInteraction(id=key,user_id=u.id,board_id=id,campaign_id=c.id,kind=data.kind))
 return {'ok':True}

class WorldInput(Strict):
 name:str=Field(min_length=2,max_length=120)
 enabled:bool=True
 public:bool=True
 joinable:bool=True
 country:str=Field(min_length=2,max_length=2)
 region:str=Field(max_length=80)
 display_order:int=Field(default=99,ge=0,le=10000)
 transport_enabled:bool=True
@router.get('/super-admin/worlds')
def worlds(u=Depends(super_admin),db=Depends(get_db)):
 from .discovery import cities
 return cities(db,include_disabled=True)
@router.put('/super-admin/worlds/{id}')
def world_edit(id:str,data:WorldInput,u=Depends(super_admin),db=Depends(get_db)):
 from .expansion import DestinationInput,edit_destination
 return edit_destination(id,DestinationInput(name=data.name,country=data.country,region=data.region,status='ACTIVE' if data.enabled else 'DISABLED',public=data.public,joinable=data.joinable,priority=data.display_order,transport_enabled=data.transport_enabled),u,db)
@router.get('/super-admin/enquiries')
def enquiries(u=Depends(super_admin),db=Depends(get_db)):return [serialize(e) for e in db.scalars(select(AdEnquiry).order_by(AdEnquiry.created_at.desc()).limit(250))]
class StatusInput(Strict):
 status:Literal['NEW','CONTACTED','QUALIFIED','DECLINED','CONVERTED']
@router.patch('/super-admin/enquiries/{id}')
def enquiry_status(id:str,data:StatusInput,u=Depends(super_admin),db=Depends(get_db)):
 e=db.get(AdEnquiry,id)
 if not e:raise HTTPException(404,'Enquiry unavailable')
 e.status=data.status;audit(db,u,'advertising.enquiry_status',id,{'status':data.status});return {'ok':True}
class CreativeInput(Strict):
 content:str=Field(max_length=6800000)
@router.post('/super-admin/creatives',status_code=201)
def upload(data:CreativeInput,u=Depends(super_admin),db=Depends(get_db)):
 try:raw=base64.b64decode(data.content,validate=True)
 except ValueError:raise HTTPException(422,'Invalid file')
 if len(raw)>5000000:raise HTTPException(413,'Use a creative smaller than 5 MB')
 if raw.startswith(b'\x89PNG\r\n\x1a\n') and len(raw)>32:
  w,h=struct.unpack('>II',raw[16:24])
  if not (1<=w<=4096 and 1<=h<=4096):raise HTTPException(422,'Image dimensions must be at most 4096 pixels')
  mime='image/png'
 elif raw.startswith(b'\xff\xd8\xff') and raw.endswith(b'\xff\xd9'):mime='image/jpeg'
 elif len(raw)>12 and raw[4:8]==b'ftyp':mime='video/mp4'
 else:raise HTTPException(422,'Upload a PNG, JPEG or MP4 creative')
 c=Creative(data=raw,mime=mime);db.add(c);db.flush();audit(db,u,'advertising.creative_uploaded',c.id);return {'id':c.id,'url':'/api/ads/creatives/'+c.id,'mime':mime}
class CampaignInput(Strict):
 advertiser:str=Field(min_length=2,max_length=160)
 name:str=Field(min_length=2,max_length=120)
 headline:str=Field(min_length=2,max_length=180)
 creative_id:str|None=None
 board_id:str
 starts_at:float=Field(allow_inf_nan=False)
 ends_at:float=Field(allow_inf_nan=False)
 cta_text:str=Field(default='Learn more',max_length=50)
 cta_url:str=Field(default='',max_length=1000)
 priority:int=Field(default=0,ge=0,le=100)
 status:Literal['draft','active','paused','archived']='draft'
@router.get('/super-admin/advertising')
def advertising(u=Depends(super_admin),db=Depends(get_db)):
 return {'boards':[serialize(b) for b in db.scalars(select(AdBoard))],'campaigns':[{**serialize(c),'creative_mime':db.get(Creative,c.creative_id).mime if c.creative_id else None} for c in db.scalars(select(AdCampaign).order_by(AdCampaign.created_at.desc()).limit(250))]}
@router.put('/super-admin/campaigns/{id}')
def campaign(id:UUID,data:CampaignInput,u=Depends(super_admin),db=Depends(get_db)):
 if not db.get(AdBoard,data.board_id):raise HTTPException(422,'Unknown board')
 if data.creative_id and not db.get(Creative,data.creative_id):raise HTTPException(422,'Upload the creative first')
 if data.ends_at<=data.starts_at:raise HTTPException(422,'End must be after start')
 url(data.cta_url);c=db.get(AdCampaign,str(id))
 if not c:c=AdCampaign(id=str(id),**data.model_dump());db.add(c)
 else:
  for k,v in data.model_dump().items():setattr(c,k,v)
 audit(db,u,'advertising.campaign_'+data.status,c.id,{'board_id':data.board_id});return serialize(c)
@router.get('/super-admin/routes')
def routes(u=Depends(super_admin),db=Depends(get_db)):
 from .transit import Route
 return [serialize(r) for r in db.scalars(select(Route))]
class RouteInput(Strict):
 frequency:int=Field(ge=300,le=3600)
 duration:int=Field(ge=60,le=900)
 fare:int=Field(ge=0,le=1000)
 capacity:int=Field(ge=2,le=40)
 enabled:bool
@router.patch('/super-admin/routes/{id}')
def route_edit(id:str,data:RouteInput,u=Depends(super_admin),db=Depends(get_db)):
 from .transit import Route
 r=db.scalar(select(Route).where(Route.id==id).with_for_update())
 if not r:raise HTTPException(404,'Route unavailable')
 for k,v in data.model_dump().items():setattr(r,k,v)
 audit(db,u,'transport.route_updated',id,data.model_dump());return serialize(r)
@router.get('/super-admin/buildings')
def buildings(q:str='',u=Depends(super_admin),db=Depends(get_db)):
 from .civic import PublicBuilding
 return [serialize(b) for b in db.scalars(select(PublicBuilding).where(PublicBuilding.name.ilike('%'+q[:80]+'%')).limit(100))]
class BuildingInput(Strict):
 enabled:bool
@router.patch('/super-admin/buildings/{id}')
def building_edit(id:str,data:BuildingInput,u=Depends(super_admin),db=Depends(get_db)):
 from .civic import PublicBuilding
 b=db.get(PublicBuilding,id)
 if not b:raise HTTPException(404,'Unsupported property; private property cannot be opened')
 b.enabled=data.enabled;audit(db,u,'building.updated',id,data.model_dump());return serialize(b)
@router.get('/super-admin/users')
def users(q:str='',u=Depends(super_admin),db=Depends(get_db)):
 from sqlalchemy import or_
 query=select(User).where(or_(User.username.ilike('%'+q[:80]+'%'),User.email.ilike('%'+q[:80]+'%'))).limit(200)
 return [{**public_user(p),'created_at':p.created_at,'suspended':p.suspended,'last_seen':(v.updated_at if (v:=db.get(Presence,p.id)) else None)} for p in db.scalars(query)]
@router.get('/super-admin/events')
def events(u=Depends(super_admin),db=Depends(get_db)):
 return [{**serialize(e),'attendance':db.scalar(select(func.count()).select_from(Attendee).where(Attendee.event_id==e.id,Attendee.state=='active'))} for e in db.scalars(select(Event).order_by(Event.created_at.desc()).limit(200))]
@router.post('/super-admin/events/{id}/end')
def event_end(id:str,u=Depends(super_admin),db=Depends(get_db)):
 from .events import finish
 e=db.get(Event,id)
 if not e:raise HTTPException(404,'Event unavailable')
 finish(db,e,'ended');audit(db,u,'event.ended',id);return {'ok':True}
@router.get('/super-admin/audit')
def audit_list(u=Depends(super_admin),db=Depends(get_db)):return [serialize(a) for a in db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(300))]

def activity(db,u):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 day=int(time.time()/86400);row=db.get(UserActivity,(u.id,day))
 if not row:db.add(UserActivity(user_id=u.id,day=day,last_seen=time.time()))
 elif time.time()-row.last_seen>60:row.last_seen=time.time()

def sample(db):
 bucket=int(time.time()/300)
 if db.scalar(select(OnlineSample.bucket).where(OnlineSample.bucket==bucket).limit(1)) is not None:return
 from .discovery import cities
 for c in cities(db):db.add(OnlineSample(bucket=bucket,city=c['id'],count=c['online']))

@router.get('/super-admin/overview')
def overview(days:int=7,start:float|None=None,end:float|None=None,u=Depends(super_admin),db=Depends(get_db)):
 from .discovery import cities
 from .transit import Ticket,Vehicle,real_passengers
 from .growth import metrics
 now=time.time();end=min(end or now,now);start=start or end-max(1,min(90,days))*86400
 if start>end or end-start>90*86400:raise HTTPException(422,'Choose a range within 90 days')
 day=int(now/86400);worlds=cities(db);daily=[{'day':d,'users':n} for d,n in db.execute(select(UserActivity.day,func.count()).where(UserActivity.day>=int(start/86400),UserActivity.day<=int(end/86400)).group_by(UserActivity.day))]
 registration=[{'day':int(t/86400),'count':n} for t,n in db.execute(select(func.floor(User.created_at/86400)*86400,func.count()).where(User.created_at>=start,User.created_at<=end).group_by(func.floor(User.created_at/86400)))]
 active=lambda n:db.scalar(select(func.count(func.distinct(UserActivity.user_id))).where(UserActivity.day>=day-n+1)) or 0
 sumkind=lambda kinds:db.scalar(select(func.coalesce(func.sum(Ledger.amount),0)).where(Ledger.currency=='credits',Ledger.kind.in_(kinds),Ledger.created_at>=start,Ledger.created_at<=end)) or 0
 trips=list(db.scalars(select(Ticket).where(Ticket.state=='aboard')));passengers=sum(len(real_passengers(db,v)) for v in {t.vehicle_id for t in trips})
 kpis={'registered_users':db.scalar(select(func.count()).select_from(User)),'online_now':sum(c['online'] for c in worlds),'daily_active':active(1),'weekly_active':active(7),'monthly_active':active(30),'new_users_today':db.scalar(select(func.count()).select_from(User).where(User.created_at>=day*86400)),'active_worlds':sum(c['enabled'] for c in worlds),'live_events':db.scalar(select(func.count()).select_from(Event).where(Event.status=='live')),'active_conversations':db.scalar(select(func.count()).select_from(MediaSession).where(MediaSession.state=='accepted',MediaSession.conversation_id==None)),'active_liveface':db.scalar(select(func.count()).select_from(MediaSession).where(MediaSession.state=='accepted',MediaSession.kind=='liveface')),'bus_passengers':passengers,'advertising_enquiries':db.scalar(select(func.count()).select_from(AdEnquiry)),'active_ad_campaigns':db.scalar(select(func.count()).select_from(AdCampaign).where(AdCampaign.status=='active',AdCampaign.starts_at<=now,AdCampaign.ends_at>now)),'credits_purchased':sumkind(['purchase']),'credits_spent':-(db.scalar(select(func.coalesce(func.sum(Ledger.amount),0)).where(Ledger.currency=='credits',Ledger.amount<0,Ledger.created_at>=start,Ledger.created_at<=end)) or 0),'transport_credits_spent':-sumkind(['transport_ticket']),'gift_credits_spent':-sumkind(['event_gift','social_gift'])}
 from .mobility import RentalLease
 from .gifts import GiftDelivery
 from .discovery import CityInterest
 from .business_spatial import BusinessInteraction
 kpis.update(vehicle_rentals=db.scalar(select(func.count()).select_from(RentalLease).where(RentalLease.ended_at==None,RentalLease.expires_at>now)),gifts_sent=db.scalar(select(func.count()).select_from(GiftDelivery).where(GiftDelivery.created_at>=start,GiftDelivery.created_at<=end)),city_requests=db.scalar(select(func.count()).select_from(CityInterest)))
 regions=[{'market':'United Kingdom','online':sum(c['online'] for c in worlds if c['country']=='GB')},{'market':'International','online':sum(c['online'] for c in worlds if c['country']!='GB')}]
 return {'markets':regions,'rentals':[{'asset':k,'count':n} for k,n in db.execute(select(RentalLease.asset_id,func.count()).where(RentalLease.started_at>=start,RentalLease.started_at<=end).group_by(RentalLease.asset_id))],'business_activity':[{'kind':k,'count':n} for k,n in db.execute(select(BusinessInteraction.kind,func.count()).where(BusinessInteraction.created_at>=start,BusinessInteraction.created_at<=end).group_by(BusinessInteraction.kind))],'kpis':kpis,'worlds':worlds,'daily_activity':daily,'registrations':registration,'online_history':[{'time':b*300,'count':n} for b,n in db.execute(select(OnlineSample.bucket,func.sum(OnlineSample.count)).where(OnlineSample.bucket>=int(start/300),OnlineSample.bucket<=int(end/300)).group_by(OnlineSample.bucket).order_by(OnlineSample.bucket))],'transport_activity':[{'route':v,'tickets':n} for v,n in db.execute(select(Vehicle.route_id,func.count(Ticket.id)).join(Ticket,Ticket.vehicle_id==Vehicle.id).where(Ticket.created_at>=start,Ticket.created_at<=end).group_by(Vehicle.route_id))],'event_activity':[{'type':k,'count':n} for k,n in db.execute(select(Event.venue_experience_type,func.count()).where(Event.created_at>=start,Event.created_at<=end).group_by(Event.venue_experience_type))],'credit_activity':[{'kind':k,'amount':n} for k,n in db.execute(select(Ledger.kind,func.sum(Ledger.amount)).where(Ledger.created_at>=start,Ledger.created_at<=end).group_by(Ledger.kind))],'ad_performance':[{'kind':k,'count':n} for k,n in db.execute(select(AdInteraction.kind,func.count()).where(AdInteraction.created_at>=start,AdInteraction.created_at<=end).group_by(AdInteraction.kind))],'growth':metrics(u,db),'history_notice':'Activity and online history begin when this release is deployed. No historic activity is invented.'}

def bootstrap_owner(db):
 email=os.getenv('SUPER_ADMIN_EMAIL','').strip().lower();password=os.getenv('SUPER_ADMIN_INITIAL_PASSWORD','');username=os.getenv('SUPER_ADMIN_USERNAME','').strip()
 if not email or not password or not username:return
 if db.scalar(select(User.id).where(User.role=='super_admin').limit(1)):return
 if len(password)<20:raise RuntimeError('Initial owner password must have at least 20 characters')
 if db.scalar(select(User.id).where((User.email==email)|(User.username==username))):raise RuntimeError('Owner bootstrap identity already exists; refusing automatic privilege escalation')
 u=User(email=email,username=username,password_hash=hash_password(password),role='super_admin',must_change_password=True,verified=True);db.add(u);db.flush();audit(db,u,'owner.bootstrap',u.id)

class RouteCreate(RouteInput):
 origin:str
 destination:str
 number:str=Field(min_length=1,max_length=8,pattern=r'^\d+$')
@router.post('/super-admin/routes',status_code=201)
def route_create(data:RouteCreate,u=Depends(super_admin),db=Depends(get_db)):
 from .transit import Route,hub
 from .discovery import catalog
 rows={c['id']:c for c in catalog(db) if c['enabled']}
 if data.origin==data.destination or data.origin not in rows or data.destination not in rows or rows[data.origin]['country']!=rows[data.destination]['country']:raise HTTPException(422,'Choose two enabled destinations in the same country')
 hub(data.origin);hub(data.destination);id=data.origin+'--'+data.destination
 if db.get(Route,id):raise HTTPException(409,'This route already exists')
 r=Route(id=id,**data.model_dump());db.add(r);audit(db,u,'transport.route_created',id);return serialize(r)
@router.get('/super-admin/stops')
def stops(u=Depends(super_admin),db=Depends(get_db)):
 from .transit import Stop
 return [serialize(s) for s in db.scalars(select(Stop))]
class StopInput(Strict):
 name:str=Field(min_length=2,max_length=120)
 enabled:bool
@router.patch('/super-admin/stops/{id}')
def stop_edit(id:str,data:StopInput,u=Depends(super_admin),db=Depends(get_db)):
 from .transit import Stop,Route
 s=db.get(Stop,id)
 if not s:raise HTTPException(404,'Stop unavailable')
 if s.offset==0 and not data.enabled and db.scalar(select(Route.id).where((Route.origin==s.city)|(Route.destination==s.city),Route.enabled==True).limit(1)):raise HTTPException(409,'Disable routes serving this city before closing the central interchange')
 s.name=data.name;s.enabled=data.enabled;audit(db,u,'transport.stop_updated',id,data.model_dump());return serialize(s)
