"""Exclusive virtual rentals and approved water activities on existing Presence/ledger."""
import math,time
from uuid import UUID
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import String,Float,Integer,Boolean,JSON,ForeignKey,select,func
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base,get_db
from .models import User,Presence,Entitlement,Config,Audit,uid
from .auth import current_user
from .core import Strict,serialize
from .economy import config,credit,balance
from .mobility_payments import currency,charge
from .geography import district,traversable,safe_step,safe_spawn,point_inside,nearest_safe_position,driving_segments,road_segments,segment_distance
from .operations import super_admin,audit
router=APIRouter(prefix='/api')
POLICY={'version':'virtual-rental-2026-1','text':'Virtual use only. Stay in the permitted world area. Rental ends at the displayed time. You may exit at any time; we return you to a safe virtual location. Rental payments buy virtual access, not a real vehicle or real-world transport. Water activities do not imply that the real place permits or is safe for swimming or boating.'}
DEFAULTS={
 'bike':{'name':'City Bike','price':10,'minutes':10,'speed':18,'acceleration':5,'brake':12,'capacity':1,'enabled':True},
 'ebike':{'name':'Electric City Bike','price':15,'minutes':10,'speed':21,'acceleration':7,'brake':14,'capacity':1,'enabled':True},
 'scooter':{'name':'City Scooter','price':20,'minutes':10,'speed':23,'acceleration':7,'brake':14,'capacity':1,'enabled':True},
 'car':{'name':'Executive Sedan','price':25,'minutes':10,'speed':32,'acceleration':8,'brake':18,'capacity':1,'enabled':True},
 'boat':{'name':'Electric Launch','price':20,'minutes':10,'speed':20,'acceleration':4,'brake':8,'capacity':1,'enabled':True},
 'swim':{'name':'Virtual Swim','price':0,'minutes':60,'speed':3,'acceleration':4,'brake':8,'capacity':1,'enabled':True}}
class RentalAsset(Base):
 __tablename__='rental_assets'
 id:Mapped[str]=mapped_column(String(100),primary_key=True)
 city:Mapped[str]=mapped_column(String(50),index=True)
 kind:Mapped[str]=mapped_column(String(20))
 x:Mapped[float]=mapped_column(Float)
 z:Mapped[float]=mapped_column(Float)
 enabled:Mapped[bool]=mapped_column(Boolean,default=True)
 water_zone_id:Mapped[str|None]=mapped_column(String(100),nullable=True)
 active_user_id:Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True,unique=True)
class WaterZone(Base):
 __tablename__='water_activity_zones'
 id:Mapped[str]=mapped_column(String(100),primary_key=True)
 city:Mapped[str]=mapped_column(String(50),index=True)
 name:Mapped[str]=mapped_column(String(160))
 source_id:Mapped[str]=mapped_column(String(80))
 boundary:Mapped[list]=mapped_column(JSON)
 holes:Mapped[list]=mapped_column(JSON,default=list)
 shore_x:Mapped[float]=mapped_column(Float)
 shore_z:Mapped[float]=mapped_column(Float)
 entry_x:Mapped[float]=mapped_column(Float)
 entry_z:Mapped[float]=mapped_column(Float)
 enabled:Mapped[bool]=mapped_column(Boolean,default=False)
class RentalLease(Base):
 __tablename__='rental_leases'
 id:Mapped[str]=mapped_column(String(36),primary_key=True)
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 asset_id:Mapped[str]=mapped_column(ForeignKey('rental_assets.id'),index=True)
 price:Mapped[int]=mapped_column(Integer)
 settings:Mapped[dict]=mapped_column(JSON)
 started_at:Mapped[float]=mapped_column(Float,default=time.time)
 expires_at:Mapped[float]=mapped_column(Float)
 ended_at:Mapped[float|None]=mapped_column(Float,nullable=True)
 heading:Mapped[float]=mapped_column(Float,default=0)
 speed:Mapped[float]=mapped_column(Float,default=0)
 last_update:Mapped[float]=mapped_column(Float,default=time.time)
 return_x:Mapped[float]=mapped_column(Float)
 return_z:Mapped[float]=mapped_column(Float)
class RentalConsent(Base):
 __tablename__='rental_policy_acceptances'
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
 version:Mapped[str]=mapped_column(String(60),primary_key=True)
 accepted_at:Mapped[float]=mapped_column(Float,default=time.time)

def movement_settings(kind,cfg):
 # Speed calibration applies to existing leases too; commercial snapshots stay intact.
 from .world import MOVEMENT
 floor=MOVEMENT['vehicleSpeeds'].get(kind)
 if floor is None:return cfg
 return {**cfg,'speed':max(floor,cfg['speed']),'acceleration':max(floor/2,cfg['acceleration'])}

DEFAULTS={kind:movement_settings(kind,cfg) for kind,cfg in DEFAULTS.items()}

def settings(db):return {kind:movement_settings(kind,cfg) for kind,cfg in config(db,'rental_types',DEFAULTS).items()}
def seed_assets(db):
 from .locations import CITIES
 from .transit import hub
 from .street_vehicles import placements
 existing=set(db.scalars(select(RentalAsset.id)))
 for c in CITIES:
  city=c['id']
  try:h=hub(city)
  except HTTPException:continue
  for i,kind in enumerate(['bike','ebike','scooter','car']):
   id=city+':'+kind
   if db.get(RentalAsset,id):continue
   # Only install at a mapped traversable point, never inside a building.
   candidates=[(h['x']+math.cos(a)*r,h['z']+math.sin(a)*r) for r in [3,5,8,12] for a in [j*math.tau/16 for j in range(16)]]
   point=next((p for p in candidates[i:]+candidates[:i] if traversable(city,*p,kind)),None)
   if point:db.add(RentalAsset(id=id,city=city,kind=kind,x=point[0],z=point[1]))
  for a in placements(city):
   if a['classification']=='RENTABLE' and a['id'] not in existing:
    db.add(RentalAsset(id=a['id'],city=city,kind=a['kind'],x=a['x'],z=a['z']))
 db.flush()

def current(db,u):
 return db.scalar(select(RentalLease).where(RentalLease.user_id==u.id,RentalLease.ended_at==None).order_by(RentalLease.started_at.desc()).limit(1))
def finish(db,u,lease=None):
 lease=lease or current(db,u)
 if not lease:return None
 asset=db.scalar(select(RentalAsset).where(RentalAsset.id==lease.asset_id).with_for_update());p=db.get(Presence,u.id)
 city=asset.city;point=(lease.return_x,lease.return_z)
 if not traversable(city,*point):point=safe_spawn(city)
 if p and asset.kind not in ['boat','swim']:
  # Pick a walkable shoulder near current position, otherwise use saved pickup.
  nearby=[(p.x+math.cos(i*math.tau/16)*r,p.z+math.sin(i*math.tau/16)*r) for r in [2,3,4,5] for i in range(16)]
  point=next((a for a in nearby if traversable(city,*a) and not traversable(city,*a,'car')),point)
 if not p:p=Presence(user_id=u.id,city=city);db.add(p)
 p.city=city;p.zone_id='world';p.mode='walk';p.x,p.z=point;p.last_move=time.time();p.updated_at=time.time();u.city=city
 lease.ended_at=time.time();lease.speed=0;asset.active_user_id=None
 audit(db,u,'rental.ended',lease.id)
 return p

def snapshot(db,u):
 lease=current(db,u)
 if not lease:return None
 if lease.expires_at<=time.time():finish(db,u,lease);return None
 a=db.get(RentalAsset,lease.asset_id)
 return {**serialize(lease),'settings':movement_settings(a.kind,lease.settings),'kind':a.kind,'name':lease.settings['name'],'city':a.city,'water':a.kind in ['boat','swim']}
def nearby(db,p):
 if p.zone_id!='world':return []
 types=settings(db);out=[]
 for a in db.scalars(select(RentalAsset).where(RentalAsset.city==p.city,RentalAsset.enabled==True,RentalAsset.x.between(p.x-130,p.x+130),RentalAsset.z.between(p.z-130,p.z+130))):
  cfg=types.get(a.kind)
  zone=db.get(WaterZone,a.water_zone_id) if a.water_zone_id else None
  if not cfg or not cfg['enabled'] or (a.water_zone_id and (not zone or not zone.enabled)):continue
  e=db.get(Entitlement,(p.user_id,a.kind));cost=0 if e and e.expires_at>time.time() else cfg['price']
  from .street_vehicles import placements
  placed=next((v for v in placements(p.city) if v['id']==a.id),{})
  out.append({k:v for k,v in {**serialize(a),**cfg,'cost':cost,'currency':currency(a.kind),'classification':'RENTABLE','distance':round(math.hypot(p.x-a.x,p.z-a.z),1),'heading':placed.get('heading',0),'available':a.kind=='swim' or a.active_user_id is None,'water':bool(zone)}.items() if k!='active_user_id'})
 return out
@router.get('/mobility')
def listing(u=Depends(current_user),db=Depends(get_db)):
 p=db.get(Presence,u.id)
 return {'policy':POLICY,'accepted':bool(db.get(RentalConsent,(u.id,POLICY['version']))),'rental':snapshot(db,u),'assets':nearby(db,p) if p else [],'credits':balance(db,u.id),'xp':balance(db,u.id,'xp')}
class Consent(Strict):
 version:str
 accepted:bool
@router.post('/mobility/policy')
def consent(data:Consent,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 if not data.accepted or data.version!=POLICY['version']:raise HTTPException(422,'Accept the current virtual rental policy')
 if not db.get(RentalConsent,(u.id,data.version)):db.add(RentalConsent(user_id=u.id,version=data.version))
 return {'accepted':True}
class Rent(Strict):
 id:UUID
 expected_cost:int=Field(ge=0)
 expected_currency:Literal['xp','credits']|None=None
@router.post('/mobility/assets/{id}/rent')
def rent(id:str,data:Rent,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 old=db.get(RentalLease,str(data.id))
 if old:
  if old.user_id!=u.id or old.asset_id!=id:raise HTTPException(409,'Rental request ID already used')
  return {'rental':serialize(old),'credits':balance(db,u.id),'xp':balance(db,u.id,'xp')}
 if current(db,u):raise HTTPException(409,'Exit your current vehicle or water activity first')
 a=db.scalar(select(RentalAsset).where(RentalAsset.id==id).with_for_update())
 if not a or not a.enabled:raise HTTPException(404,'Vehicle unavailable')
 cfg=settings(db).get(a.kind)
 if not cfg or not cfg['enabled']:raise HTTPException(409,'This rental is disabled')
 if a.active_user_id and a.kind!='swim':raise HTTPException(409,'Someone is already using this vehicle')
 p=db.get(Presence,u.id)
 if not p or p.zone_id!='world' or p.city!=a.city or math.hypot(p.x-a.x,p.z-a.z)>10:raise HTTPException(409,'Approach the parked vehicle or activity entrance')
 from .growth import require_access
 require_access(db,u,a.city)
 if not db.get(RentalConsent,(u.id,POLICY['version'])):raise HTTPException(409,'Accept the virtual rental policy first')
 zone=db.get(WaterZone,a.water_zone_id) if a.water_zone_id else None
 if a.kind in ['boat','swim'] and (not zone or not zone.enabled):raise HTTPException(409,'Water activity is not approved here')
 if not zone and not traversable(a.city,a.x,a.z,a.kind):raise HTTPException(409,'Vehicle pickup is unavailable')
 entitlement=db.get(Entitlement,(u.id,a.kind));cost=0 if entitlement and entitlement.expires_at>time.time() else cfg['price']
 if data.expected_cost!=cost:raise HTTPException(409,{'code':'PRICE_CHANGED','cost':cost,'message':'Review the current rental price'})
 denomination=charge(db,u.id,a.kind,cost,a.id,'rental:'+str(data.id),data.expected_currency)
 if zone:heading=math.atan2(zone.entry_x-zone.shore_x,zone.entry_z-zone.shore_z)
 else:
  roads=driving_segments(a.city) if a.kind=='car' else road_segments(a.city)
  v,w=min(roads,key=lambda ends:segment_distance(a.x,a.z,*ends));heading=math.atan2(w[0]-v[0],w[1]-v[1])
 lease=RentalLease(heading=heading,id=str(data.id),user_id=u.id,asset_id=a.id,price=cost,settings={**cfg,'currency':denomination},expires_at=time.time()+cfg['minutes']*60,return_x=p.x,return_z=p.z)
 db.add(lease);a.active_user_id=u.id if a.kind!='swim' else None;p.mode=a.kind;p.x,p.z=(zone.entry_x,zone.entry_z) if zone else (a.x,a.z);p.last_move=time.time();p.updated_at=time.time()
 db.flush();audit(db,u,'rental.started',lease.id)
 return {'rental':snapshot(db,u),'credits':balance(db,u.id),'xp':balance(db,u.id,'xp')}
class Drive(Strict):
 throttle:float=Field(ge=-1,le=1,allow_inf_nan=False)
 steer:float=Field(ge=-1,le=1,allow_inf_nan=False)
 city:str|None=Field(default=None,max_length=50)
 zone:str|None=Field(default=None,max_length=100)
@router.post('/mobility/drive')
def drive(data:Drive,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update());lease=current(db,u);p=db.get(Presence,u.id)
 if not lease or not p:raise HTTPException(409,'No active vehicle')
 if (data.city is not None and data.city!=p.city) or (data.zone is not None and data.zone!=p.zone_id):raise HTTPException(409,'Your location changed. Movement was cleared.')
 if lease.expires_at<=time.time():finish(db,u,lease);return {'position':serialize(p),'rental':None,'exited':True}
 a=db.get(RentalAsset,lease.asset_id);cfg=movement_settings(a.kind,lease.settings);now=time.time();dt=min(.3,max(0,now-lease.last_update))
 if p.city!=a.city or p.zone_id!='world':raise HTTPException(409,'Exit your rental before entering another location')
 acceleration=cfg['acceleration']*data.throttle if data.throttle>0 else -cfg['brake']*abs(data.throttle) if data.throttle<0 else -cfg['acceleration']*.5
 lease.speed=max(0,min(cfg['speed'],lease.speed+acceleration*dt))
 # Heading grows clockwise in x/z space. Positive input is the right control.
 turning=(1.5 if a.kind=='car' else 2.4)/(1+lease.speed/max(1,cfg['speed']))
 lease.heading=(lease.heading+data.steer*dt*turning*min(1,lease.speed/2))%math.tau
 dx,dz=math.sin(lease.heading)*lease.speed*dt,math.cos(lease.heading)*lease.speed*dt
 old=(p.x,p.z)
 if a.water_zone_id:
  zone=db.get(WaterZone,a.water_zone_id)
  if not zone or not zone.enabled:finish(db,u,lease);return {'position':serialize(p),'rental':None,'exited':True}
  steps=max(1,math.ceil(math.hypot(dx,dz)/.2))
  for _ in range(steps):
   x,z=p.x+dx/steps,p.z+dz/steps
   if point_inside(x,z,zone.boundary) and not any(point_inside(x,z,h) for h in zone.holes):p.x,p.z=x,z
   else:lease.speed=0;break
 else:p.x,p.z=safe_step(p.city,p.x,p.z,dx,dz,a.kind)
 blocked=bool(lease.speed>.1 and dt>.03 and math.dist(old,(p.x,p.z))<.01)
 from .motion_diagnostics import observe
 observe(u.id,p.city,p.zone_id,a.kind,p.x,p.z,data.throttle>0,blocked)
 if blocked:lease.speed=0
 p.mode=a.kind;p.last_move=now;p.updated_at=now;lease.last_update=now
 return {'position':{'x':p.x,'z':p.z,'mode':p.mode,'zone_id':p.zone_id,'heading':lease.heading,'last_move':now,'blocked':blocked},'rental':snapshot(db,u)}
@router.post('/mobility/exit')
def leave(u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update());p=finish(db,u)
 return {'position':serialize(p) if p else None,'rental':None}
class TypeInput(Strict):
 name:str=Field(min_length=2,max_length=80)
 price:int=Field(ge=0,le=10000)
 minutes:int=Field(ge=1,le=120)
 speed:float=Field(ge=1,le=120,allow_inf_nan=False)
 acceleration:float=Field(gt=0,le=60,allow_inf_nan=False)
 brake:float=Field(gt=0,le=30,allow_inf_nan=False)
 capacity:Literal[1]=1
 enabled:bool=True
@router.get('/super-admin/vehicles')
def admin_vehicles(u=Depends(super_admin),db=Depends(get_db)):
 return {'types':{k:{**v,'currency':currency(k)} for k,v in settings(db).items()},'assets':[serialize(a) for a in db.scalars(select(RentalAsset).order_by(RentalAsset.city))],'water_zones':[serialize(z) for z in db.scalars(select(WaterZone))],'active_rentals':db.scalar(select(func.count()).select_from(RentalLease).where(RentalLease.ended_at==None,RentalLease.expires_at>time.time()))}
@router.put('/super-admin/vehicles/types/{kind}')
def update_type(kind:str,data:TypeInput,u=Depends(super_admin),db=Depends(get_db)):
 if kind not in DEFAULTS:raise HTTPException(422,'Unsupported vehicle type')
 if kind not in ['bike','ebike','car'] and (data.speed>45 or data.acceleration>20):raise HTTPException(422,'This activity retains its existing speed and acceleration limits')
 db.scalar(select(User.id).where(User.id==u.id).with_for_update());row=db.scalar(select(Config).where(Config.key=='rental_types').with_for_update())
 value={k:movement_settings(k,v) for k,v in (row.value if row else DEFAULTS).items()};value[kind]=data.model_dump()
 from .world import OUTDOOR_RUN_SPEED
 if not (OUTDOOR_RUN_SPEED<value['bike']['speed']<=value['ebike']['speed']<value['car']['speed'] and value['scooter']['speed']<value['car']['speed'] and value['swim']['speed']<value['boat']['speed']):raise HTTPException(422,'Preserve outdoor walk < run < bike < car, scooter < car and swim < boat')
 if row:row.value=value
 else:db.add(Config(key='rental_types',value=value))
 audit(db,u,'vehicle.type_updated',kind,data.model_dump());return value[kind]
class AssetInput(Strict):
 city:str
 kind:Literal['bike','ebike','scooter','car']
 x:float=Field(allow_inf_nan=False)
 z:float=Field(allow_inf_nan=False)
 enabled:bool=True
@router.put('/super-admin/vehicles/assets/{id}')
def edit_asset(id:str,data:AssetInput,u=Depends(super_admin),db=Depends(get_db)):
 if len(id)>100:raise HTTPException(422,'Asset ID too long')
 if not traversable(data.city,data.x,data.z,data.kind):raise HTTPException(422,'Choose a valid mapped pickup point')
 a=db.scalar(select(RentalAsset).where(RentalAsset.id==id).with_for_update())
 if a and a.active_user_id:raise HTTPException(409,'Wait for the active rental to end')
 if not a:a=RentalAsset(id=id);db.add(a)
 for k,v in data.model_dump().items():setattr(a,k,v)
 audit(db,u,'vehicle.asset_updated',id,data.model_dump());return {'ok':True}
class WaterInput(Strict):
 city:str
 source_id:str=Field(max_length=80)
 name:str=Field(min_length=2,max_length=160)
 shore_x:float=Field(allow_inf_nan=False)
 shore_z:float=Field(allow_inf_nan=False)
 entry_x:float=Field(allow_inf_nan=False)
 entry_z:float=Field(allow_inf_nan=False)
 enabled:bool=False
@router.put('/super-admin/water/{id}')
def edit_water(id:str,data:WaterInput,u=Depends(super_admin),db=Depends(get_db)):
 if len(id)>85:raise HTTPException(422,'Zone ID too long')
 f=next((f for f in district(data.city)['features'] if str(f['id'])==data.source_id and (f['tags'].get('natural')=='water' or f['tags'].get('waterway')=='riverbank') and len(f['points'])>=4),None)
 if not f or not point_inside(data.entry_x,data.entry_z,f['points']) or any(point_inside(data.entry_x,data.entry_z,h) for h in f.get('holes',[])):raise HTTPException(422,'Select an entry inside a mapped water polygon')
 if not traversable(data.city,data.shore_x,data.shore_z) or math.hypot(data.shore_x-data.entry_x,data.shore_z-data.entry_z)>15:raise HTTPException(422,'Provide a safe mapped shore within 15 virtual metres')
 z=db.scalar(select(WaterZone).where(WaterZone.id==id).with_for_update())
 assets=list(db.scalars(select(RentalAsset).where(RentalAsset.water_zone_id==id).with_for_update()))
 if any(a.active_user_id for a in assets) or db.scalar(select(RentalLease.id).where(RentalLease.asset_id.in_([a.id for a in assets]),RentalLease.ended_at==None).limit(1)):raise HTTPException(409,'Wait for current water activities to end')
 if not z:z=WaterZone(id=id);db.add(z)
 for k,v in data.model_dump().items():setattr(z,k,v)
 z.boundary=f['points'];z.holes=f.get('holes',[])
 for kind in ['boat','swim']:
  a=db.get(RentalAsset,id+':'+kind)
  if not a:a=RentalAsset(id=id+':'+kind,kind=kind,water_zone_id=id);db.add(a)
  a.city=data.city;a.x=data.shore_x;a.z=data.shore_z;a.enabled=data.enabled
 audit(db,u,'water.zone_updated',id,data.model_dump());return {'ok':True}

def maintenance(db):
 for user_id in db.scalars(select(RentalLease.user_id).where(RentalLease.ended_at==None,RentalLease.expires_at<=time.time()).distinct()):
  u=db.scalar(select(User).where(User.id==user_id).with_for_update());lease=current(db,u)
  if lease and lease.expires_at<=time.time():finish(db,u,lease)


def seed_water(db):
 import json
 from pathlib import Path
 path=Path(__file__).resolve().parents[1]/'data'/'virtual-water-zones.json'
 if not path.exists():return
 for row in json.loads(path.read_text()):
  if db.get(WaterZone,row['id']):continue
  f=next((f for f in district(row['city'])['features'] if str(f['id'])==row['source_id'] and f['tags'].get('natural')=='water'),None)
  if not f or not traversable(row['city'],row['shore_x'],row['shore_z']) or not point_inside(row['entry_x'],row['entry_z'],f['points']) or any(point_inside(row['entry_x'],row['entry_z'],h) for h in f.get('holes',[])):continue
  db.add(WaterZone(**row,boundary=f['points'],holes=f.get('holes',[])))
  for kind in ['boat','swim']:db.add(RentalAsset(id=row['id']+':'+kind,city=row['city'],kind=kind,x=row['shore_x'],z=row['shore_z'],water_zone_id=row['id'],enabled=row['enabled']))
 db.flush()
