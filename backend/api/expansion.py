"""Destination catalogue and demand. Interest never grants world access."""
import secrets
import json, re, unicodedata, hashlib
from pathlib import Path
import time
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import String, Integer, Float, Boolean, JSON, ForeignKey, UniqueConstraint, select, func
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, get_db
from .models import User, Config, Audit, Notification
from .core import Strict, serialize
from .auth import current_user
from .operations import super_admin, audit

router = APIRouter(prefix='/api')
STATES = Literal['ACTIVE', 'COMING_SOON', 'REQUESTABLE', 'QUALIFIED', 'IN_PREPARATION', 'DISABLED']
# Catalogue metadata only. These are not fabricated playable maps or businesses.
INTERNATIONAL = [
 ('paris','Paris','FR','Europe'),('berlin','Berlin','DE','Europe'),('amsterdam','Amsterdam','NL','Europe'),
 ('madrid','Madrid','ES','Europe'),('barcelona','Barcelona','ES','Europe'),('rome','Rome','IT','Europe'),
 ('milan','Milan','IT','Europe'),('dublin','Dublin','IE','Europe'),
 ('new-york','New York','US','North America'),('los-angeles','Los Angeles','US','North America'),
 ('miami','Miami','US','North America'),('toronto','Toronto','CA','North America'),('vancouver','Vancouver','CA','North America'),
 ('dubai','Dubai','AE','Gulf'),('abu-dhabi','Abu Dhabi','AE','Gulf'),('riyadh','Riyadh','SA','Gulf'),
 ('jeddah','Jeddah','SA','Gulf'),('doha','Doha','QA','Gulf'),
 ('mumbai','Mumbai','IN','Asia'),('bengaluru','Bengaluru','IN','Asia'),('kochi','Kochi','IN','Asia'),
 ('singapore','Singapore','SG','Asia'),('tokyo','Tokyo','JP','Asia'),('seoul','Seoul','KR','Asia'),
 ('bangkok','Bangkok','TH','Asia'),('shanghai','Shanghai','CN','Asia'),
 ('sydney','Sydney','AU','Australia'),('melbourne','Melbourne','AU','Australia'),
]
REQUESTABLE = [
 ('glasgow','Glasgow','GB','Scotland'),('belfast','Belfast','GB','Northern Ireland'),
 ('sheffield','Sheffield','GB','England'),('luton','Luton','GB','England'),
 ('chicago','Chicago','US','North America'),('las-vegas','Las Vegas','US','North America'),
 ('boston','Boston','US','North America'),('montreal','Montreal','CA','North America'),
 ('delhi','Delhi','IN','Asia'),('chennai','Chennai','IN','Asia'),('hyderabad','Hyderabad','IN','Asia'),
 ('kuala-lumpur','Kuala Lumpur','MY','Asia'),('osaka','Osaka','JP','Asia'),('busan','Busan','KR','Asia'),
 ('beijing','Beijing','CN','Asia'),('shenzhen','Shenzhen','CN','Asia'),('sharjah','Sharjah','AE','Gulf'),
 ('alula','AlUla','SA','Gulf'),('brisbane','Brisbane','AU','Australia'),
]

def request_countries():
 return json.loads((Path(__file__).resolve().parents[1]/'data/request-places.json').read_text())

def place_key(name):
 return ''.join(c for c in unicodedata.normalize('NFKD',name).casefold() if c.isalnum())

def request_id(country,name):
 slug=re.sub('[^a-z0-9]+','-',unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode().lower()).strip('-')
 return slug if slug else 'place-'+hashlib.sha256((country+place_key(name)).encode()).hexdigest()[:20]

for country in request_countries():
 for name in country['places']:
  if not any(c==country['country'] and place_key(n)==place_key(name) for _,n,c,_ in REQUESTABLE):
   REQUESTABLE.append((request_id(country['country'],name),name,country['country'],''))

class Destination(Base):
 __tablename__ = 'destinations'
 id:Mapped[str] = mapped_column(String(80),primary_key=True)
 name:Mapped[str] = mapped_column(String(120))
 country:Mapped[str] = mapped_column(String(2))
 region:Mapped[str] = mapped_column(String(80),default='')
 status:Mapped[str] = mapped_column(String(20),default='REQUESTABLE',index=True)
 public:Mapped[bool] = mapped_column(Boolean,default=True)
 joinable:Mapped[bool] = mapped_column(Boolean,default=True)
 priority:Mapped[int] = mapped_column(Integer,default=100)
 threshold:Mapped[int|None] = mapped_column(Integer,nullable=True)
 transport_enabled:Mapped[bool] = mapped_column(Boolean,default=True)
 feature_flags:Mapped[dict] = mapped_column(JSON,default=dict)
 catalogue_group:Mapped[str] = mapped_column(String(20),default='request')
 updated_at:Mapped[float] = mapped_column(Float,default=time.time)

class DemandShare(Base):
 __tablename__ = 'destination_demand_shares'
 code:Mapped[str] = mapped_column(String(40),primary_key=True,default=lambda:secrets.token_urlsafe(18))
 user_id:Mapped[str] = mapped_column(ForeignKey('users.id'),index=True)
 destination_id:Mapped[str] = mapped_column(ForeignKey('destinations.id'))
 created_at:Mapped[float] = mapped_column(Float,default=time.time)
 __table_args__ = (UniqueConstraint('user_id','destination_id'),)

class DemandShareAction(Base):
 __tablename__ = 'destination_demand_share_actions'
 id:Mapped[str] = mapped_column(String(36),primary_key=True)
 code:Mapped[str] = mapped_column(ForeignKey('destination_demand_shares.code'),index=True)
 channel:Mapped[str] = mapped_column(String(20))
 created_at:Mapped[float] = mapped_column(Float,default=time.time)

def flag(country):
 return ''.join(chr(127397+ord(c)) for c in country) if len(country)==2 and country.isalpha() else '🌍'

def map_ready(id):
 from .locations import CITIES
 from pathlib import Path
 return id in {c['id'] for c in CITIES} and (Path(__file__).resolve().parents[1]/'data'/(id+'.json.gz')).is_file()

def seed_catalog(db):
 from .locations import CITIES
 existing=set(db.scalars(select(Destination.id)))
 legacy=db.get(Config,'world_settings'); settings=legacy.value if legacy else {}
 for c in CITIES:
  if c['id'] in existing:continue
  old=settings.get(c['id'],{})
  db.add(Destination(id=c['id'],name=old.get('name',c['name']),country=old.get('country',c.get('country','GB')),region=old.get('region',c.get('region','')),status='IN_PREPARATION' if c.get('requires_activation') else 'ACTIVE' if old.get('enabled',True) else 'DISABLED',public=old.get('public',True),joinable=old.get('joinable',True),priority=old.get('display_order',50),transport_enabled=old.get('transport_enabled',True),catalogue_group='home' if c.get('country','GB')=='GB' else 'international'))
  existing.add(c['id'])
 for group,rows in [('international',INTERNATIONAL),('request',REQUESTABLE)]:
  for id,name,country,region in rows:
   if id not in existing:
    db.add(Destination(id=id,name=name,country=country,region=region,status='REQUESTABLE',catalogue_group=group));existing.add(id)
 if not db.get(Config,'city_demand'):db.add(Config(key='city_demand',value={'threshold':5000}))
 db.flush()

def default_threshold(db):
 row=db.get(Config,'city_demand')
 return max(1,int(row.value.get('threshold',5000))) if row else 5000

def destination_view(db,d,*,threshold=None):
 from .locations import CITIES
 installed=next((c for c in CITIES if c['id']==d.id),{})
 enabled=d.status=='ACTIVE' and bool(installed)
 return {**installed,**serialize(d),'flag':flag(d.country),'enabled':enabled,'display_order':d.priority,'interest_threshold':d.threshold or (default_threshold(db) if threshold is None else threshold),'map_ready':bool(installed),'world_provider':'openstreetmap-bundled' if installed else None,'simulated':bool(installed)}

def qualified(db,d,total):
 if d.status in ['REQUESTABLE','COMING_SOON'] and total >= (d.threshold or default_threshold(db)):
  d.status='QUALIFIED';d.updated_at=time.time()
  db.add(Audit(action='destination.qualified',target=d.id,details={'interested':total}))
  from .growth import GrowthEvent
  db.add(GrowthEvent(kind='city_demand_qualified',destination_id=d.id))
  for uid in db.scalars(select(User.id).where(User.role=='super_admin',User.suspended==False)):
   db.add(Notification(user_id=uid,kind='destination.qualified',body=d.name+' reached its city-demand goal. Review world readiness before activating.',source=d.id))

class InterestInput(Strict):
 source:str=Field(default='world-explorer',max_length=60)
 invite_code:str=Field(default='',max_length=40)

def add_interest(db,u,id,data=None):
 from .discovery import CityInterest
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 d=db.scalar(select(Destination).where(Destination.id==id).with_for_update())
 if not d or not d.public or d.status in ['ACTIVE','DISABLED']:raise HTTPException(422,'This destination is not accepting requests')
 data=data or InterestInput();inv=db.get(DemandShare,data.invite_code) if data.invite_code else None
 if data.invite_code and (not inv or inv.destination_id!=id):raise HTTPException(422,'This request link is unavailable')
 old=db.get(CityInterest,(u.id,id))
 if not old:
  db.add(CityInterest(user_id=u.id,city=id,source=data.source,invite_code=inv.code if inv and inv.user_id!=u.id else ''));db.flush()
  db.add(Audit(actor_id=u.id,action='city_interest_joined',target=id))
  from .growth import event
  event(db,u,'future_place_requested',id);event(db,u,'city_interest_added',id)
  if inv and inv.user_id!=u.id:event(db,u,'city_interest_conversion',id,code=inv.code)
 total=db.scalar(select(func.count()).select_from(CityInterest).where(CityInterest.city==id)) or 0
 qualified(db,d,total)
 return {'city':id,'joined':True,'counted':not bool(old),'interested_count':total,'status':d.status,'interest_threshold':d.threshold or default_threshold(db)}

@router.post('/destinations/{id}/interest')
def interest(id:str,data:InterestInput,u=Depends(current_user),db=Depends(get_db)):
 return add_interest(db,u,id,data)

@router.post('/destinations/{id}/viewed',status_code=202)
def viewed(id:str,u=Depends(current_user),db=Depends(get_db)):
 from .growth import event
 d=db.get(Destination,id)
 if not d or not d.public or d.status in ['ACTIVE','DISABLED']:raise HTTPException(404,'Future place unavailable')
 event(db,u,'future_place_viewed',id)
 return {'ok':True}

@router.get('/request-places')
def request_catalogue(db=Depends(get_db)):
 from .discovery import cities
 future=[d for d in cities(db) if d['status'] not in ['ACTIVE','DISABLED']]
 return {'countries':[{**c,'flag':flag(c['country']),'places':[d for d in future if d['country']==c['country']]} for c in request_countries()]}

class CustomPlace(Strict):
 country:str=Field(pattern=r'^[A-Z]{2}$')
 name:str=Field(min_length=2,max_length=80)

@router.post('/request-places',status_code=201)
def custom_place(data:CustomPlace,u=Depends(current_user),db=Depends(get_db)):
 from .discovery import CityInterest
 from .growth import event
 if data.country not in {c['country'] for c in request_countries()}:raise HTTPException(422,'Choose a supported country')
 name=' '.join(unicodedata.normalize('NFKC',data.name).split())
 if len(name)<2 or sum(c.isalpha() for c in name)<2 or any(not(c.isalpha() or c in " '-’.") for c in name) or len(place_key(name))<2:
  raise HTTPException(422,'Enter a city or place name using letters, spaces, apostrophes or hyphens')
 # Shared row lock serializes normalized custom-name deduplication across users.
 db.scalar(select(Config).where(Config.key=='city_demand').with_for_update())
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 d=next((d for d in db.scalars(select(Destination).where(Destination.country==data.country)) if place_key(d.name)==place_key(name)),None)
 if d and d.status=='ACTIVE':raise HTTPException(409,{'code':'USE_WORLD_ACCESS','destination_id':d.id,'message':'This world is already active. Add it to Your Worlds or share to unlock it.'})
 if d and d.status=='DISABLED':raise HTTPException(422,'This place is not accepting requests')
 if d and d.public:return {**destination_view(db,d),**add_interest(db,u,d.id),'review_pending':False}
 prior=db.get(CityInterest,(u.id,d.id)) if d else None
 if not prior:
  requests=db.scalar(select(func.count()).select_from(Audit).where(Audit.actor_id==u.id,Audit.action=='destination.custom_requested',Audit.created_at>time.time()-86400)) or 0
  if requests>=3:raise HTTPException(429,'You can suggest three new places per day. Please check existing places first.')
 if not d:
  id='request-'+data.country.lower()+'-'+hashlib.sha256((data.country+place_key(name)).encode()).hexdigest()[:24]
  d=Destination(id=id,name=name,country=data.country,status='REQUESTABLE',public=False,joinable=False,catalogue_group='custom')
  db.add(d);db.flush()
 if not prior:
  db.add(CityInterest(user_id=u.id,city=d.id,source='custom-request'))
  db.add(Audit(actor_id=u.id,action='destination.custom_requested',target=d.id))
  event(db,u,'future_place_requested',d.id);event(db,u,'city_interest_added',d.id)
 db.flush()
 return {'id':d.id,'name':d.name,'flag':flag(d.country),'review_pending':True,'counted':not bool(prior),'message':'Your interest is saved. The team will review this place before publishing its request page.'}

@router.post('/destinations/{id}/share-link')
def share_link(id:str,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 d=db.get(Destination,id)
 if not d or not d.public or d.status in ['ACTIVE','DISABLED']:raise HTTPException(404,'Only future places accept demand invitations')
 row=db.scalar(select(DemandShare).where(DemandShare.user_id==u.id,DemandShare.destination_id==id))
 if not row:row=DemandShare(user_id=u.id,destination_id=id);db.add(row);db.flush()
 return {'code':row.code,'path':'/request/'+row.code}

@router.get('/destination-requests/{code}')
def shared_request(code:str,db=Depends(get_db)):
 from .discovery import cities
 row=db.get(DemandShare,code)
 if not row:raise HTTPException(404,'Request link unavailable')
 city=next((d for d in cities(db) if d['id']==row.destination_id),None)
 if not city:raise HTTPException(404,'Destination unavailable')
 return {'destination':city,'code':code} # Deliberately no sharer identity.

@router.post('/destination-requests/{code}/opened',status_code=202)
def opened(code:str,db=Depends(get_db)):
 from .growth import GrowthEvent
 shared_request(code,db)
 db.add(GrowthEvent(kind='city_request_link_opened',invite_code=code,destination_id=db.get(DemandShare,code).destination_id))
 return {'ok':True}

class ShareInput(Strict):
 id:UUID
 channel:Literal['whatsapp','facebook','instagram','x','email','sms','copy','native','more']
@router.post('/destination-requests/{code}/shared',status_code=202)
def shared(code:str,data:ShareInput,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update());row=db.get(DemandShare,code)
 if not row or row.user_id!=u.id:raise HTTPException(403,'Create your own request link')
 old=db.get(DemandShareAction,str(data.id))
 if old:
  if old.code!=code or old.channel!=data.channel:raise HTTPException(409,'Share ID already used')
 else:
  db.add(DemandShareAction(id=str(data.id),code=code,channel=data.channel))
  from .growth import event
  event(db,u,'city_request_shared',row.destination_id,data.channel,code)
 return {'ok':True,'interest_counted':False}

@router.get('/super-admin/demand')
def demand(u=Depends(super_admin),db=Depends(get_db)):
 from .discovery import cities,CityInterest
 from .growth import GrowthEvent
 return {'default_threshold':default_threshold(db),'destinations':cities(db,include_disabled=True),
 'shares_by_channel':dict(db.execute(select(DemandShareAction.channel,func.count()).group_by(DemandShareAction.channel)).all()),
 'link_opens':db.scalar(select(func.count()).select_from(GrowthEvent).where(GrowthEvent.kind.in_(['city_demand_link_opened','city_request_link_opened']))) or 0,
 'interest_conversions':db.scalar(select(func.count()).select_from(CityInterest).where(CityInterest.invite_code!='')) or 0}

class DemandSettings(Strict):
 threshold:int=Field(ge=1,le=10000000)
@router.put('/super-admin/demand/settings')
def demand_settings(data:DemandSettings,u=Depends(super_admin),db=Depends(get_db)):
 cfg=db.scalar(select(Config).where(Config.key=='city_demand').with_for_update())
 if not cfg:cfg=Config(key='city_demand',value={});db.add(cfg)
 cfg.value={'threshold':data.threshold};cfg.updated_at=time.time()
 from .discovery import CityInterest
 counts=dict(db.execute(select(CityInterest.city,func.count()).group_by(CityInterest.city)).all())
 for d in db.scalars(select(Destination).order_by(Destination.id).with_for_update()):qualified(db,d,counts.get(d.id,0))
 audit(db,u,'destination.threshold_default','city_demand',data.model_dump());return {'ok':True}

class DestinationInput(Strict):
 name:str=Field(min_length=2,max_length=120)
 country:str=Field(pattern=r'^[A-Z]{2}$')
 region:str=Field(default='',max_length=80)
 status:STATES
 public:bool=True
 joinable:bool=True
 priority:int=Field(default=100,ge=0,le=10000)
 threshold:int|None=Field(default=None,ge=1,le=10000000)
 transport_enabled:bool=True
 feature_flags:dict[str,bool]=Field(default_factory=dict,max_length=30)
@router.put('/super-admin/destinations/{id}')
def edit_destination(id:str,data:DestinationInput,u=Depends(super_admin),db=Depends(get_db)):
 d=db.scalar(select(Destination).where(Destination.id==id).with_for_update())
 if not d:raise HTTPException(404,'Destination unavailable')
 if data.status=='ACTIVE' and not map_ready(id):raise HTTPException(409,{'code':'WORLD_DATA_REQUIRED','message':'Install and validate approved world data before activating this destination.'})
 for k,v in data.model_dump().items():setattr(d,k,v)
 d.updated_at=time.time()
 from .discovery import CityInterest
 qualified(db,d,db.scalar(select(func.count()).select_from(CityInterest).where(CityInterest.city==id)) or 0)
 audit(db,u,'destination.updated',id,data.model_dump())
 if d.status=='ACTIVE':
  from .world_content import seed_world
  seed_world(db,d.id,d.name)
 return destination_view(db,d)
