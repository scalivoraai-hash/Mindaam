"""Restricted platform operations and advertising. No arbitrary infrastructure access."""
import os,time,base64,hashlib,struct
from uuid import UUID
from typing import Literal
from urllib.parse import urlparse
from fastapi import APIRouter,Depends,HTTPException,Request,Response,Query
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
 day:Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
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

def seed_inventory(db,only_city=None):
 from .locations import CITIES
 from .expansion import Destination
 from .billboard_placement import prepared_placements
 for city in CITIES:
  if only_city is not None and city['id']!=only_city:continue
  destination=db.scalar(select(Destination).where(Destination.id==city['id']).with_for_update())
  if not destination or destination.status!='ACTIVE' or not destination.public or not destination.joinable:continue
  marker='billboard_initial_v2:'+city['id']
  if db.get(Config,marker):continue
  points=prepared_placements(city['id'])
  if len(points)!=3:continue # Fail closed on stale/unsafe geometry; no obstructing fallback.
  ids=[]
  for index,(x,z) in enumerate(points,1):
   id=city['id']+f'-central-{index:02d}';row=db.get(AdBoard,id)
   if row:
    # Preserve identity and campaigns while repairing the original unsafe hub.
    row.x,row.z=x,z
   else:db.add(AdBoard(id=id,city=city['id'],name=city['name']+f' · Placement {index}',x=x,z=z))
   ids.append(id)
  db.add(Config(key=marker,value={'boards':ids}))
  db.add(Audit(actor_id=None,action='advertising.initial_placements',target=city['id'],details={'boards':ids}))

class BoardInput(Strict):
 city:str=Field(max_length=50)
 name:str=Field(min_length=2,max_length=120)
 x:float=Field(allow_inf_nan=False)
 z:float=Field(allow_inf_nan=False)
 enabled:bool=True

@router.put('/super-admin/billboards/{id}')
def board_save(id:str,data:BoardInput,u=Depends(super_admin),db=Depends(get_db)):
 from .expansion import Destination
 from .billboard_placement import safe
 import math,re
 if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',id):raise HTTPException(422,'Invalid placement ID')
 destination=db.scalar(select(Destination).where(Destination.id==data.city).with_for_update())
 if not destination or destination.status!='ACTIVE' or not destination.public or not destination.joinable:raise HTTPException(422,'Choose an active city')
 if not safe(data.city,data.x,data.z):raise HTTPException(422,'Placement must clear roads, buildings, water and restricted land')
 row=db.scalar(select(AdBoard).where(AdBoard.id==id).with_for_update())
 if row and row.city!=data.city:raise HTTPException(409,'Create a new placement to change city; existing campaign history must remain intact')
 others=list(db.scalars(select(AdBoard).where(AdBoard.city==data.city,AdBoard.id!=id,AdBoard.enabled==True)))
 if data.enabled and (len(others)>=12 or any(math.hypot(data.x-b.x,data.z-b.z)<30 for b in others)):raise HTTPException(409,'Use a separated placement; at most 12 active boards per city')
 if not row:row=AdBoard(id=id,**data.model_dump());db.add(row)
 else:
  for k,v in data.model_dump().items():setattr(row,k,v)
 audit(db,u,'advertising.placement_saved',id,data.model_dump());db.flush();return serialize(row)

@router.delete('/super-admin/billboards/{id}')
def board_remove(id:str,u=Depends(super_admin),db=Depends(get_db)):
 row=db.scalar(select(AdBoard).where(AdBoard.id==id).with_for_update())
 if not row:raise HTTPException(404,'Placement unavailable')
 row.enabled=False
 # Archive placement without destroying campaigns, enquiries or interaction history.
 audit(db,u,'advertising.placement_removed',id,{'city':row.city});return {'ok':True,'archived':True}

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
 if raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff'):
  from PIL import Image,UnidentifiedImageError
  from io import BytesIO
  try:
   with Image.open(BytesIO(raw)) as picture:
    if picture.format not in {'PNG','JPEG'} or not (1<=picture.width<=4096 and 1<=picture.height<=4096):raise ValueError('Unsupported dimensions')
    picture.load()
    output=BytesIO();picture.convert('RGB').save(output,format='JPEG',quality=90)
    raw=output.getvalue();mime='image/jpeg'
  except (ValueError,OSError,Image.DecompressionBombError):raise HTTPException(422,'Upload a valid image of at most 4096 pixels per side')
 elif len(raw)>12 and raw[4:8]==b'ftyp':mime='video/mp4'
 else:raise HTTPException(422,'Upload a PNG, JPEG or MP4 creative')
 if len(raw)>5000000:raise HTTPException(413,'Decoded creative must be smaller than 5 MB')
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
 from sqlalchemy import or_,case
 query=select(User).where(or_(User.username.ilike('%'+q[:80]+'%'),User.email.ilike('%'+q[:80]+'%'))).limit(200)
 return [{**public_user(p),'created_at':p.created_at,'suspended':p.suspended,'last_seen':(v.updated_at if (v:=db.get(Presence,p.id)) else None)} for p in db.scalars(query)]
@router.get('/super-admin/events')
def events(q:str='',u=Depends(super_admin),db=Depends(get_db)):
 query=select(Event)
 if q:query=query.where(or_(Event.title.ilike('%'+q[:80]+'%'),Event.city==q,Event.host_id==q,Event.status==q,Event.id==q))
 return [{**serialize(e),'attendance':db.scalar(select(func.count()).select_from(Attendee).where(Attendee.event_id==e.id,Attendee.state=='active'))} for e in db.scalars(query.order_by(Event.created_at.desc()).limit(200))]
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
 now=time.time();end=min(end if end is not None else now,now);start=start if start is not None else end-max(1,min(90,days))*86400
 import math
 if not math.isfinite(start) or not math.isfinite(end):raise HTTPException(422,'Use finite UTC timestamps')
 if start>end or end-start>90*86400:raise HTTPException(422,'Choose a range within 90 days')
 day=int(now/86400);worlds=cities(db,include_disabled=True);daily=[{'day':d,'users':n} for d,n in db.execute(select(UserActivity.day,func.count()).where(UserActivity.day>=int(start/86400),UserActivity.day<=int(end/86400)).group_by(UserActivity.day))]
 from .admin_analytics import day_series,enrich,online_series
 registration=day_series(db,User.created_at,[func.count().label('count')],start,end)
 active=lambda n:db.scalar(select(func.count(func.distinct(UserActivity.user_id))).where(UserActivity.day>=day-n+1)) or 0
 sumkind=lambda kinds:db.scalar(select(func.coalesce(func.sum(Ledger.amount),0)).where(Ledger.currency=='credits',Ledger.kind.in_(kinds),Ledger.created_at>=start,Ledger.created_at<=end)) or 0
 passengers=db.scalar(select(func.count()).select_from(Ticket).join(Presence,Presence.user_id==Ticket.user_id).join(User,User.id==Ticket.user_id).where(Ticket.state=='aboard',Presence.zone_id=='bus:'+Ticket.vehicle_id,Presence.updated_at>now-45,User.suspended==False,User.id.in_(select(Session.user_id).where(Session.expires_at>now)))) or 0
 kpis={'registered_users':db.scalar(select(func.count()).select_from(User)),'online_now':sum(c['online'] for c in worlds),'daily_active':active(1),'weekly_active':active(7),'monthly_active':active(30),'new_users_today':db.scalar(select(func.count()).select_from(User).where(User.created_at>=day*86400)),'active_worlds':sum(c['enabled'] for c in worlds),'live_events':db.scalar(select(func.count()).select_from(Event).where(Event.status=='live')),'active_conversations':db.scalar(select(func.count()).select_from(MediaSession).where(MediaSession.state=='accepted',MediaSession.conversation_id==None)),'active_liveface':db.scalar(select(func.count()).select_from(MediaSession).where(MediaSession.state=='accepted',MediaSession.kind=='liveface')),'bus_passengers':passengers,'advertising_enquiries':db.scalar(select(func.count()).select_from(AdEnquiry)),'active_ad_campaigns':db.scalar(select(func.count()).select_from(AdCampaign).where(AdCampaign.status=='active',AdCampaign.starts_at<=now,AdCampaign.ends_at>now)),'credits_purchased':sumkind(['purchase']),'credits_spent':-(db.scalar(select(func.coalesce(func.sum(Ledger.amount),0)).where(Ledger.currency=='credits',Ledger.amount<0,Ledger.created_at>=start,Ledger.created_at<=end)) or 0),'transport_credits_spent':-sumkind(['transport_ticket']),'gift_credits_spent':-sumkind(['event_gift','social_gift'])}
 from .mobility import RentalLease
 from .gifts import GiftDelivery
 from .discovery import CityInterest
 from .business_spatial import BusinessInteraction
 kpis.update(vehicle_rentals=db.scalar(select(func.count()).select_from(RentalLease).where(RentalLease.ended_at==None,RentalLease.expires_at>now)),gifts_sent=db.scalar(select(func.count()).select_from(GiftDelivery).where(GiftDelivery.created_at>=start,GiftDelivery.created_at<=end)),city_requests=db.scalar(select(func.count()).select_from(CityInterest)))
 kpis.update(verified_users=db.scalar(select(func.count()).select_from(User).where(User.verified==True)),suspended_users=db.scalar(select(func.count()).select_from(User).where(User.suspended==True)),new_users_7_days=db.scalar(select(func.count()).select_from(User).where(User.created_at>=now-7*86400)),new_users_30_days=db.scalar(select(func.count()).select_from(User).where(User.created_at>=now-30*86400)),configured_worlds=len(worlds),inactive_worlds=sum(not c['enabled'] for c in worlds),inactive_users_30_days=max(0,kpis['registered_users']-active(30)))
 regions=[{'market':'United Kingdom','online':sum(c['online'] for c in worlds if c['country']=='GB')},{'market':'International','online':sum(c['online'] for c in worlds if c['country']!='GB')}]
 result={'markets':regions,'rentals':[{'asset':k,'count':n} for k,n in db.execute(select(RentalLease.asset_id,func.count()).where(RentalLease.started_at>=start,RentalLease.started_at<=end).group_by(RentalLease.asset_id))],'business_activity':[{'kind':k,'count':n} for k,n in db.execute(select(BusinessInteraction.kind,func.count()).where(BusinessInteraction.created_at>=start,BusinessInteraction.created_at<=end).group_by(BusinessInteraction.kind))],'kpis':kpis,'worlds':worlds,'daily_activity':daily,'registrations':registration,'online_history':online_series(db,start,end),'transport_activity':[{'route':v,'tickets':n} for v,n in db.execute(select(Vehicle.route_id,func.count(Ticket.id)).join(Ticket,Ticket.vehicle_id==Vehicle.id).where(Ticket.created_at>=start,Ticket.created_at<=end).group_by(Vehicle.route_id))],'event_activity':[{'type':k,'count':n} for k,n in db.execute(select(Event.venue_experience_type,func.count()).where(Event.created_at>=start,Event.created_at<=end).group_by(Event.venue_experience_type))],'credit_activity':[{'kind':k,'amount':n} for k,n in db.execute(select(Ledger.kind,func.sum(Ledger.amount)).where(Ledger.currency=='credits',Ledger.created_at>=start,Ledger.created_at<=end).group_by(Ledger.kind))],'ad_performance':[{'kind':k,'count':n} for k,n in db.execute(select(AdInteraction.kind,func.count()).where(AdInteraction.created_at>=start,AdInteraction.created_at<=end).group_by(AdInteraction.kind))],'history_notice':'Activity and online history begin when this release is deployed. No historic activity is invented.'}
 return enrich(db,result,start,end,now)

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

# Control-centre read models extend the existing operations router and role gate.
from fastapi import Query
from sqlalchemy import or_,case

def operator_user(db, person):
 from .economy import balance
 p=db.get(Presence,person.id)
 last=db.scalar(select(func.max(UserActivity.last_seen)).where(UserActivity.user_id==person.id))
 online=bool(p and p.updated_at>time.time()-90 and not person.suspended and db.scalar(select(Session.id).where(Session.user_id==person.id,Session.expires_at>time.time()).limit(1)))
 return {'id':person.id,'username':person.username,'display_name':(person.profile or {}).get('display_name',''),'email':person.email,'role':person.role,'created_at':person.created_at,'last_seen':max(last or 0,p.updated_at if p else 0) or None,'online':online,'city':p.city if online else person.city,'suspended':person.suspended,'verified':person.verified,'credits':balance(db,person.id),'xp':balance(db,person.id,'xp')}

@router.get('/super-admin/directory')
def directory(q:str='',status:Literal['all','active','suspended']='all',sort:Literal['newest','oldest','username']='newest',page:int=Query(1,ge=1),limit:int=Query(25,ge=1,le=100),u=Depends(super_admin),db=Depends(get_db)):
 filters=[or_(User.username.ilike('%'+q[:80]+'%'),User.email.ilike('%'+q[:80]+'%'),User.id==q)]
 if status!='all':filters.append(User.suspended==(status=='suspended'))
 order={'newest':User.created_at.desc(),'oldest':User.created_at.asc(),'username':User.username.asc()}[sort]
 total=db.scalar(select(func.count()).select_from(User).where(*filters))
 rows=db.scalars(select(User).where(*filters).order_by(order,User.id).offset((page-1)*limit).limit(limit))
 from .admin_records import directory_rows
 return {'items':directory_rows(db,list(rows)),'total':total,'page':page,'limit':limit,'presence_window_seconds':90}

@router.get('/super-admin/users/{id}/detail')
def user_detail(id:str,tab:Literal['overview','profile','wallet','social','events','cities','payments','audit','activity','reports']='overview',page:int=Query(1,ge=1),u=Depends(super_admin),db=Depends(get_db)):
 from .models import Social,Report
 from .commerce import Payment
 from .venue_rentals import purchased_available,VenueBooking
 from .event_tickets import EventTicket
 from .economy import balance
 person=db.get(User,id)
 if not person:raise HTTPException(404,'User not found')
 result={'user':operator_user(db,person),'tab':tab,'page':page,'limit':25}
 if tab in {'overview','profile'}:result['profile']={k:v for k,v in (person.profile or {}).items() if k in {'display_name','bio','languages','theme'}}
 elif tab=='activity':query=select(UserActivity).where(UserActivity.user_id==id).order_by(UserActivity.day.desc())
 elif tab=='reports':query=select(Report).where(Report.target_id==id).order_by(Report.created_at.desc(),Report.id)
 elif tab=='wallet':
  result.update(purchased_available=purchased_available(db,id),credits=balance(db,id),xp=balance(db,id,'xp'),attribution_notice='Purchased availability follows the existing purchased-first venue eligibility policy; promotional grants are never purchases.')
  query=select(Ledger).where(Ledger.user_id==id).order_by(Ledger.created_at.desc(),Ledger.id)
 elif tab=='social':
  result['relationships']=[{'kind':k,'count':n} for k,n in db.execute(select(Social.kind,func.count()).where(Social.actor==id).group_by(Social.kind))]
  result['privacy_notice']='Private messages, media and precise device location are not exposed.'
  return result
 elif tab=='events':
  result['created']=[{'id':e.id,'title':e.title,'status':e.status,'city':e.city} for e in db.scalars(select(Event).where(Event.host_id==id).limit(100))]
  result['reservations']=[serialize(b) for b in db.scalars(select(VenueBooking).where(VenueBooking.user_id==id).order_by(VenueBooking.created_at.desc()).limit(100))]
  query=select(EventTicket).where(EventTicket.user_id==id).order_by(EventTicket.created_at.desc())
 elif tab=='cities':
  from .growth import WorldAccess
  query=select(WorldAccess).where(WorldAccess.user_id==id)
 elif tab=='payments':query=select(Payment).where(Payment.user_id==id).order_by(Payment.created_at.desc())
 elif tab=='audit':query=select(Audit).where(Audit.target==id).order_by(Audit.created_at.desc())
 if tab not in {'overview','profile'}:
  result['total']=db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
  result['items']=[serialize(row) for row in db.scalars(query.offset((page-1)*25).limit(25))]
  if tab=='payments':
   for row in result['items']:
    row.pop('checkout_url',None);row.pop('request_key',None)
 return result

class OperatorAdjustment(Strict):
 request_id:UUID
 currency:Literal['credits','xp']
 amount:int=Field(ge=-100000,le=100000,strict=True)
 reason:str=Field(min_length=12,max_length=500)
 purpose:Literal['promotion','support','correction','xp_award']
 confirmed:bool

@router.post('/super-admin/users/{id}/adjustments')
def adjust_wallet(id:str,data:OperatorAdjustment,u=Depends(super_admin),db=Depends(get_db)):
 from .economy import credit,config
 if len(data.reason.strip())<12:raise HTTPException(422,'Provide a meaningful reason of at least 12 characters')
 if not data.confirmed or data.amount==0:raise HTTPException(422,'Confirm a non-zero adjustment')
 if data.currency=='xp' and data.purpose not in {'xp_award','correction'}:raise HTTPException(422,'Choose an XP purpose')
 if data.currency=='credits' and data.purpose=='xp_award':raise HTTPException(422,'XP awards cannot issue Credits')
 if data.amount<0 and data.purpose!='correction':raise HTTPException(422,'Debits require a documented correction')
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 target=db.get(User,id)
 if not target:raise HTTPException(404,'User not found')
 if target.role in {'admin','super_admin'}:raise HTTPException(409,'Privileged-account adjustments require separate operational review')
 limits=config(db,'operator_adjustment_limits',{'credits':1000,'xp':5000,'daily_actions':20})
 key='operator:'+u.id+':'+str(data.request_id)
 old=db.scalar(select(Ledger).where(Ledger.user_id==id,Ledger.idempotency_key==key))
 if old and old.currency!=data.currency:raise HTTPException(409,'Request ID already used for a different currency')
 reason_hash=hashlib.sha256((data.reason.strip()+':'+data.purpose).encode()).hexdigest()
 source='admin:'+u.id+':'+reason_hash[:32]
 if not old:
  if abs(data.amount)>int(limits.get(data.currency,0)):raise HTTPException(409,'Amount exceeds the configured operator limit; separate elevated approval is required')
  count=db.scalar(select(func.count()).select_from(Audit).where(Audit.actor_id==u.id,Audit.action=='wallet.adjusted',Audit.created_at>time.time()-86400))
  if count>=int(limits.get('daily_actions',20)):raise HTTPException(429,'Daily adjustment limit reached')
 row=credit(db,id,data.amount,'admin_'+data.purpose,source,key,data.currency)
 if not old:audit(db,u,'wallet.adjusted',id,{'transaction_id':row.id,'currency':data.currency,'amount':data.amount,'reason':data.reason.strip(),'purpose':data.purpose,'before':row.previous_balance,'after':row.balance,'request_id':str(data.request_id)})
 return {'transaction':serialize(row),'replayed':bool(old)}

@router.get('/super-admin/finance')
def finance(days:int=Query(30,ge=1,le=90),u=Depends(super_admin),db=Depends(get_db)):
 from .commerce import Payment
 from .subscriptions import CustomerSubscription,SubscriptionInvoice
 start=time.time()-days*86400
 confirmed=Payment.status.in_(['paid','refunded','partially_refunded'])
 payments=list(db.scalars(select(Payment).where(Payment.created_at>=start).order_by(Payment.created_at.desc()).limit(1000)))
 gross,refunds,paid_count=db.execute(select(func.coalesce(func.sum(Payment.amount_pence),0),func.coalesce(func.sum(Payment.refunded_pence),0),func.count()).where(Payment.created_at>=start,confirmed)).one()
 pending_count=db.scalar(select(func.count()).select_from(Payment).where(Payment.created_at>=start,Payment.status=='pending'))
 by_product=[{'product':sku,'count':n,'gross_pence':gross,'refund_pence':refund} for sku,n,gross,refund in db.execute(select(Payment.sku,func.count(),func.sum(Payment.amount_pence),func.sum(Payment.refunded_pence)).where(Payment.created_at>=start,confirmed).group_by(Payment.sku))]
 from .admin_analytics import day_series
 by_day=day_series(db,Payment.created_at,[func.sum(case((confirmed,Payment.amount_pence),else_=0)).label('gross_pence'),func.sum(case((confirmed,Payment.refunded_pence),else_=0)).label('refund_pence')],start,time.time())
 rows=[{k:getattr(p,k) for k in ['id','user_id','sku','amount_pence','refunded_pence','status','dispute_status','provider_id','created_at']} for p in payments]
 return {'currency':'GBP','amount_unit':'pence','days':days,'by_product':by_product,'by_day':by_day,'outstanding_pc':db.scalar(select(func.coalesce(func.sum(Ledger.amount),0)).where(Ledger.currency=='credits')),'failed_payments':db.scalar(select(func.count()).select_from(Payment).where(Payment.created_at>=start,Payment.status.in_(['failed','expired','cancelled']))),'gross_pence':gross,'refund_pence':refunds,'net_sales_pence':gross-refunds,'successful_payments':paid_count,'pending_payments':pending_count,'payments':rows,'limited_to_latest':1000,'active_subscriptions':db.scalar(select(func.count()).select_from(CustomerSubscription).where(CustomerSubscription.status=='active',CustomerSubscription.paid_through>time.time())),'subscription_revenue_pence':None,'settlement_pence':None,'fees_pence':None,'notice':'Reporting groups payments by checkout creation time, not settlement time. Paid rows reflect verified provider processing; pending rows are excluded from sales. Net sales are not bank settlement. Subscription invoice cash amounts and processing fees are not recorded, so those figures are unavailable. PC and XP are not GBP revenue.'}

@router.get('/super-admin/records/{kind}')
def operational_records(kind:str,page:int=Query(1,ge=1,le=10000),q:str=Query('',max_length=80),days:int=Query(0,ge=0,le=365),limit:int=Query(25,ge=1,le=100),status:str=Query('',max_length=40),sort:Literal['newest','oldest','name']='newest',event_id:str=Query('',max_length=100),user_id:str=Query('',max_length=100),u=Depends(super_admin),db=Depends(get_db)):
 from .admin_records import rows
 return rows(db,kind,page,limit,q,status,sort,days,event_id,user_id)

@router.get('/super-admin/records/{kind}/{id}')
def operational_detail(kind:str,id:str,u=Depends(super_admin),db=Depends(get_db)):
 from .admin_records import detail
 return detail(db,kind,id)

@router.get('/super-admin/events/{id}/participants')
def event_participants(id:str,page:int=Query(1,ge=1,le=10000),limit:int=Query(25,ge=1,le=100),u=Depends(super_admin),db=Depends(get_db)):
 query=select(Attendee,User.username).join(User,User.id==Attendee.user_id).where(Attendee.event_id==id)
 total=db.scalar(select(func.count()).select_from(query.subquery()))
 return {'items':[{**serialize(a),'username':name,'id':a.user_id} for a,name in db.execute(query.order_by(Attendee.joined_at.desc(),Attendee.user_id).offset((page-1)*limit).limit(limit))],'total':total,'page':page,'limit':limit}

class OperatorStatus(Strict):
 suspended:bool
 reason:str=Field(min_length=12,max_length=500)
@router.patch('/super-admin/users/{id}/status')
def operator_status(id:str,data:OperatorStatus,u=Depends(super_admin),db=Depends(get_db)):
 from .core import suspend,Suspension
 if len(data.reason.strip())<12:raise HTTPException(422,'Provide a meaningful reason of at least 12 characters')
 result=suspend(id,Suspension(suspended=data.suspended),u,db)
 audit(db,u,'user.status_review',id,{'reason':data.reason,'suspended':data.suspended})
 return result

class AdjustmentReview(Base):
 __tablename__='operator_adjustment_reviews'
 id:Mapped[str]=mapped_column(String(36),primary_key=True)
 requester_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 target_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 currency:Mapped[str]=mapped_column(String(10))
 amount:Mapped[int]=mapped_column(Integer)
 purpose:Mapped[str]=mapped_column(String(30))
 reason:Mapped[str]=mapped_column(String(500))
 state:Mapped[str]=mapped_column(String(20),default='pending')
 reviewer_id:Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True)
 transaction_id:Mapped[str|None]=mapped_column(ForeignKey('wallet_transactions.id'),nullable=True)
 created_at:Mapped[float]=mapped_column(Float,default=time.time)

@router.post('/super-admin/users/{id}/adjustment-requests')
def request_adjustment(id:str,data:OperatorAdjustment,u=Depends(super_admin),db=Depends(get_db)):
 if len(data.reason.strip())<12:raise HTTPException(422,'Provide a meaningful reason of at least 12 characters')
 if not data.confirmed or data.amount==0:raise HTTPException(422,'Confirm a non-zero adjustment')
 if (data.currency=='xp' and data.purpose not in {'xp_award','correction'}) or (data.currency=='credits' and data.purpose=='xp_award') or (data.amount<0 and data.purpose!='correction'):raise HTTPException(422,'Invalid adjustment purpose')
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 target=db.get(User,id)
 if not target:raise HTTPException(404,'User not found')
 if target.role in {'admin','super_admin'}:raise HTTPException(409,'Privileged-account adjustments are not permitted')
 old=db.get(AdjustmentReview,str(data.request_id))
 values={'requester_id':u.id,'target_id':id,'currency':data.currency,'amount':data.amount,'purpose':data.purpose,'reason':data.reason.strip()}
 if old:
  if any(getattr(old,k)!=v for k,v in values.items()):raise HTTPException(409,'Request ID already used with different details')
  return serialize(old)
 if db.scalar(select(func.count()).select_from(AdjustmentReview).where(AdjustmentReview.requester_id==u.id,AdjustmentReview.created_at>time.time()-86400))>=20:raise HTTPException(429,'Daily review request limit reached')
 row=AdjustmentReview(id=str(data.request_id),**values);db.add(row);db.flush()
 audit(db,u,'wallet.review_requested',id,{'review_id':row.id,**values});return serialize(row)

class ReviewDecision(Strict):
 approve:bool
 reason:str=Field(min_length=12,max_length=500)
 confirmed:bool

@router.get('/super-admin/adjustment-requests')
def adjustment_requests(page:int=Query(1,ge=1),u=Depends(super_admin),db=Depends(get_db)):
 return {'items':[serialize(r) for r in db.scalars(select(AdjustmentReview).order_by(AdjustmentReview.created_at.desc()).offset((page-1)*25).limit(25))],'total':db.scalar(select(func.count()).select_from(AdjustmentReview)),'page':page,'limit':25}

@router.post('/super-admin/adjustment-requests/{id}/decision')
def decide_adjustment(id:str,data:ReviewDecision,u=Depends(super_admin),db=Depends(get_db)):
 from .economy import credit
 if len(data.reason.strip())<12:raise HTTPException(422,'Provide a meaningful review reason')
 if not data.confirmed:raise HTTPException(422,'Confirm the review decision')
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 row=db.scalar(select(AdjustmentReview).where(AdjustmentReview.id==id).with_for_update())
 if not row:raise HTTPException(404,'Review not found')
 if row.requester_id==u.id:raise HTTPException(403,'A different Super Admin must review this request')
 if row.state!='pending':
  if row.state==('approved' if data.approve else 'rejected'):return serialize(row)
  raise HTTPException(409,'Review already decided')
 if data.approve:
  requester=db.get(User,row.requester_id);target=db.get(User,row.target_id)
  if not requester or requester.suspended or requester.must_change_password or requester.role!='super_admin':raise HTTPException(409,'Requesting administrator is no longer eligible')
  if not target or target.role in {'admin','super_admin'}:raise HTTPException(409,'Target is no longer eligible')
  if row.created_at<time.time()-7*86400:raise HTTPException(409,'Review request expired; request a new review')
  if db.scalar(select(func.count()).select_from(Audit).where(Audit.actor_id==u.id,Audit.action=='wallet.review_approved',Audit.created_at>time.time()-86400))>=20:raise HTTPException(429,'Daily approval limit reached')
  transaction=credit(db,row.target_id,row.amount,'admin_'+row.purpose,'review:'+row.id,'operator-review:'+row.id,row.currency)
  row.transaction_id=transaction.id
  details={'before':transaction.previous_balance,'after':transaction.balance,'transaction_id':transaction.id}
 else:details={}
 row.state='approved' if data.approve else 'rejected';row.reviewer_id=u.id
 audit(db,u,'wallet.review_'+row.state,row.target_id,{'review_id':row.id,'requester_id':row.requester_id,'currency':row.currency,'amount':row.amount,'reason':data.reason.strip(),**details})
 return serialize(row)

class AdjustmentLimits(Strict):
 credits:int=Field(ge=0,le=10000,strict=True)
 xp:int=Field(ge=0,le=50000,strict=True)
 daily_actions:int=Field(ge=0,le=100,strict=True)
 reason:str=Field(min_length=12,max_length=500)
 confirmed:bool

@router.get('/super-admin/adjustment-limits')
def adjustment_limits(u=Depends(super_admin),db=Depends(get_db)):
 from .economy import config
 return config(db,'operator_adjustment_limits',{'credits':1000,'xp':5000,'daily_actions':20})

@router.put('/super-admin/adjustment-limits')
def save_adjustment_limits(data:AdjustmentLimits,u=Depends(super_admin),db=Depends(get_db)):
 if len(data.reason.strip())<12:raise HTTPException(422,'Provide a meaningful policy reason')
 if not data.confirmed:raise HTTPException(422,'Confirm limit changes')
 before=adjustment_limits(u,db);value=data.model_dump(exclude={'reason','confirmed'})
 row=db.get(Config,'operator_adjustment_limits')
 if row:row.value=value;row.updated_at=time.time()
 else:db.add(Config(key='operator_adjustment_limits',value=value))
 audit(db,u,'wallet.limits_updated','operator_adjustment_limits',{'before':before,'after':value,'reason':data.reason.strip()});return value

@router.get('/super-admin/system-health')
def system_health(u=Depends(super_admin),db=Depends(get_db)):
 from .db import APP_ENV
 db.scalar(select(User.id).limit(1))
 return {'environment':APP_ENV,'database':'query succeeded','release_sha':os.getenv('RELEASE_SHA') or os.getenv('GIT_SHA') or 'Not supplied by runtime','media_credentials_configured':all(os.getenv(k) for k in ['LIVEKIT_URL','LIVEKIT_API_KEY','LIVEKIT_API_SECRET']),'stripe_credentials_configured':bool(os.getenv('STRIPE_SECRET_KEY')),'stripe_webhook_configured':bool(os.getenv('STRIPE_WEBHOOK_SECRET')),'notice':'Configuration presence does not establish provider connectivity or account verification. Media and Stripe acceptance must run against the deployed environment. No cloud credentials are exposed.'}

@router.get('/super-admin/live')
def live_operations(city:str='',u=Depends(super_admin),db=Depends(get_db)):
 now=time.time()
 query=select(Presence).join(User,User.id==Presence.user_id).where(Presence.updated_at>now-90,User.suspended==False,select(Session.id).where(Session.user_id==User.id,Session.expires_at>now).exists())
 if city:query=query.where(Presence.city==city)
 rows=list(db.scalars(query));cities={};zones={}
 for p in rows:
  cities[p.city]=cities.get(p.city,0)+1;key=(p.city,p.zone_id or 'world');zones[key]=zones.get(key,0)+1
 return {'as_of':now,'window_seconds':90,'online_users':len(rows),'cities':[{'city':k,'online':v} for k,v in sorted(cities.items())],'zones':[{'city':c,'zone':z,'online':v} for (c,z),v in sorted(zones.items())],'notice':'Authenticated presence updated within 90 seconds. Zone IDs describe virtual spaces, never device GPS. Multiple sessions do not duplicate a user.'}
