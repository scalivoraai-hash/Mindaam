"""Attributed map listings enrich the existing business identity and tenant boundary."""
import math,time,json
from pathlib import Path
from urllib.parse import urlparse,urlencode
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import String,Float,Boolean,JSON,ForeignKey,select,func
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base,get_db
from .models import User,Presence,Audit,uid
from .auth import current_user
from .core import Strict,serialize
from .operations import super_admin
from .commerce import Business,tenant,audit,public_business
from .civic import PublicBuilding,InteriorVisit,entrance,entry_position
from .geography import district,point_inside
router=APIRouter(prefix='/api')
class BusinessSpatial(Base):
 __tablename__='business_spatial_profiles'
 business_id:Mapped[str]=mapped_column(ForeignKey('businesses.id'),primary_key=True)
 source_id:Mapped[str|None]=mapped_column(String(140),unique=True,nullable=True)
 data_source:Mapped[str]=mapped_column(String(500),default='Business submitted')
 category:Mapped[str]=mapped_column(String(80),default='')
 website:Mapped[str]=mapped_column(String(1200),default='')
 opening_hours:Mapped[str]=mapped_column(String(600),default='')
 parent_building_id:Mapped[str|None]=mapped_column(ForeignKey('public_buildings.id'),nullable=True,index=True)
 mall_id:Mapped[str|None]=mapped_column(String(100),nullable=True)
 floor:Mapped[str]=mapped_column(String(30),default='')
 unit:Mapped[str]=mapped_column(String(60),default='')
 entrance:Mapped[dict]=mapped_column(JSON,default=dict)
 placement_confidence:Mapped[str]=mapped_column(String(40),default='UNCERTAIN')
 claimed_status:Mapped[str]=mapped_column(String(30),default='unclaimed')
 assistant_enabled:Mapped[bool]=mapped_column(Boolean,default=False)
 assistant_status:Mapped[str]=mapped_column(String(30),default='COMING_SOON')
 assistant_configuration:Mapped[dict]=mapped_column(JSON,default=dict)
 business_knowledge_source:Mapped[str]=mapped_column(String(500),default='')
class BusinessMember(Base):
 __tablename__='business_members'
 business_id:Mapped[str]=mapped_column(ForeignKey('businesses.id'),primary_key=True)
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
 role:Mapped[str]=mapped_column(String(30),default='BUSINESS_MANAGER')
class BusinessInteraction(Base):
 __tablename__='business_interactions'
 id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
 business_id:Mapped[str]=mapped_column(ForeignKey('businesses.id'),index=True)
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
 kind:Mapped[str]=mapped_column(String(30))
 created_at:Mapped[float]=mapped_column(Float,default=time.time)

def template(category):
 return {'coffee_shop':'cafe','cafe':'cafe','restaurant':'restaurant','fast_food':'restaurant','pub':'restaurant','clothes':'fashion','shoes':'fashion','boutique':'fashion','cosmetics':'beauty','beauty':'beauty','hairdresser':'beauty','supermarket':'grocery','convenience':'grocery','greengrocer':'grocery','electronics':'electronics','mobile_phone':'electronics','computer':'electronics','pharmacy':'pharmacy','bank':'bank','office':'office'}.get(category,'retail')
def safe_url(value):
 parsed=urlparse(value or '')
 return value if parsed.scheme in ['https','http'] and parsed.hostname and not parsed.username and not parsed.password else ''
def seed_businesses(db):
 from .locations import CITIES
 profiles=list(db.scalars(select(BusinessSpatial)));existing={p.source_id for p in profiles};profile_ids={p.business_id for p in profiles}
 buildings={b.id:b for b in db.scalars(select(PublicBuilding))};known={}
 for b in db.scalars(select(Business)):known.setdefault((b.city,b.name),[]).append(b)
 new_businesses=[];new_buildings=[];new_profiles=[]
 extra_path=Path(__file__).resolve().parents[1]/'data'/'business-enrichment.json'
 extra=json.loads(extra_path.read_text()) if extra_path.exists() else {}
 for city in CITIES:
  geo=district(city['id']);origin=geo['origin'];features=geo['features'];malls=[]
  for f in features:
   t=f['tags']
   if t.get('shop')!='mall' or not t.get('name') or len(f['points'])<4:continue
   id=city['id']+':'+str(f['id']);pts=f['points'];point=[sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts)]
   entry=entrance(city['id'],point)
   if not entry:
    entry=next((entrance(city['id'],point) for point in pts if entrance(city['id'],point)),None)
   if not entry:continue
   if id not in buildings:
    pb=PublicBuilding(id=id,city=city['id'],name=t['name'][:160],template='mall',source_id=str(f['id']),x=entry[0],z=entry[1]);buildings[id]=pb;new_buildings.append(pb)
   malls.append((id,f))
  for f in features:
   t=dict(f['tags']);t.update(extra.get(city['id'],{}).get('tags',{}).get(str(f['id']),{}))
   if not t.get('name') or not (t.get('shop') or t.get('amenity') in ['cafe','restaurant','fast_food','pub','bank','pharmacy']) or t.get('shop')=='mall' or t.get('access') in ['private','no']:continue
   source=city['id']+':osm:'+str(f['id'])
   if source in existing:continue
   pts=f['points'];x=sum(p[0] for p in pts)/len(pts);z=sum(p[1] for p in pts)/len(pts)
   lat=origin['lat']-z/111320;lon=origin['lon']+x/(111320*math.cos(math.radians(origin['lat'])))
   # Never duplicate an existing claimed merchant at the same mapped place.
   b=next((b for b in known.get((city['id'],t['name'][:120]),[]) if abs(b.latitude-lat)<.0001 and abs(b.longitude-lon)<.0001),None)
   if b and b.id in profile_ids:continue
   if not b:
    import uuid
    b=Business(id=str(uuid.uuid5(uuid.NAMESPACE_URL,'mylilworlds:'+source)),owner_id=None,name=t['name'][:120],city=city['id'],address=' '.join(t[k] for k in ['addr:housenumber','addr:street','addr:postcode'] if t.get(k)),description='',latitude=lat,longitude=lon,status='listed');new_businesses.append(b);known.setdefault((city['id'],b.name),[]).append(b)
   parent=next(((id,m) for id,m in malls if point_inside(x,z,m['points']) and not any(point_inside(x,z,h) for h in m.get('holes',[]))),None)
   entry=entrance(city['id'],[x,z]);category=t.get('shop') or t.get('amenity')
   profile=BusinessSpatial(business_id=b.id,source_id=source,data_source='OpenStreetMap contributors · ODbL',category=category,website=safe_url(t.get('website') or t.get('contact:website')),opening_hours=t.get('opening_hours',''),parent_building_id=parent[0] if parent else None,mall_id=parent[0] if parent else None,floor=t.get('level',''),unit=t.get('addr:unit',''),entrance={'x':entry[0],'z':entry[1]} if entry else {},placement_confidence='CONFIRMED_INSIDE_PARENT' if parent else 'CONFIRMED_STANDALONE' if t.get('building') and t.get('building') not in ['retail','commercial'] else 'UNCERTAIN',claimed_status='claimed' if b.owner_id else 'unclaimed')
   new_profiles.append(profile);profile_ids.add(b.id)
   # Category templates are virtual representations, not claimed replicas.
   if entry or parent:
    if parent:pb=buildings[parent[0]];entry=(pb.x,pb.z)
    storeid='store:'+b.id
    if storeid not in buildings:
     pb=PublicBuilding(id=storeid,city=b.city,name=b.name,template=template(category),source_id=source,x=entry[0],z=entry[1]);buildings[storeid]=pb;new_buildings.append(pb)
   existing.add(source)
 # Keep each PostgreSQL executemany operation within the normal statement budget.
 for rows in [new_businesses,new_buildings,new_profiles]:
  for start in range(0,len(rows),200):db.add_all(rows[start:start+200]);db.flush()

def get_business(db,id):
 b=db.get(Business,id)
 if not b or b.status not in ['listed','verified']:raise HTTPException(404,'Business unavailable')
 return b
def card(db,b):
 p=db.get(BusinessSpatial,b.id);parent=db.get(PublicBuilding,p.parent_building_id) if p and p.parent_building_id else None
 info=serialize(p) if p else {'category':b.signage.get('category',''),'website':'','opening_hours':b.signage.get('opening_hours',''),'claimed_status':'claimed' if b.owner_id else 'unclaimed','data_source':'Business submitted','placement_confidence':'UNCERTAIN'}
 info.pop('assistant_configuration',None);info.pop('business_knowledge_source',None)
 coords={'lat':b.latitude,'lon':b.longitude};directions='https://www.google.com/maps/dir/?'+urlencode({'api':1,'destination':f'{b.latitude},{b.longitude}'})
 return {**public_business(b),**info,'parent_name':parent.name if parent else None,'coordinates':coords,'directions_url':directions,'enterable':bool(db.get(PublicBuilding,'store:'+b.id)),'assistant_enabled':False,'assistant_status':'COMING_SOON'}
def track(db,u,id,kind):
 if not db.scalar(select(BusinessInteraction.id).where(BusinessInteraction.user_id==u.id,BusinessInteraction.business_id==id,BusinessInteraction.kind==kind,BusinessInteraction.created_at>time.time()-30)):
  db.add(BusinessInteraction(user_id=u.id,business_id=id,kind=kind))
@router.get('/business-cards/{id}')
def business_card(id:str,u=Depends(current_user),db=Depends(get_db)):
 b=get_business(db,id);track(db,u,id,'profile_view');return card(db,b)
@router.get('/business-pois/{city}/{source_id}')
def poi_card(city:str,source_id:str,u=Depends(current_user),db=Depends(get_db)):
 p=db.scalar(select(BusinessSpatial).where(BusinessSpatial.source_id==city+':osm:'+source_id))
 if not p:raise HTTPException(404,'No attributable business listing for this place')
 return business_card(p.business_id,u,db)
class InteractionInput(Strict):
 kind:str=Field(pattern='^(website_click|directions_click|claim_interest)$')
@router.post('/business-cards/{id}/interaction')
def interaction(id:str,data:InteractionInput,u=Depends(current_user),db=Depends(get_db)):
 get_business(db,id);track(db,u,id,data.kind);return {'ok':True}
@router.get('/buildings/{id}/directory')
def directory(id:str,u=Depends(current_user),db=Depends(get_db)):
 b=db.get(PublicBuilding,id);p=db.get(Presence,u.id)
 if not b or not p or p.zone_id!='building:'+id:raise HTTPException(403,'Enter this building to use its directory')
 rows=list(db.scalars(select(BusinessSpatial).where(BusinessSpatial.parent_building_id==id).order_by(BusinessSpatial.business_id)))
 return {'building':serialize(b),'notice':'Directory placement is a virtual template; it is not a surveyed floor plan.','shops':[{**card(db,db.get(Business,s.business_id)),'door':{'x':-9 if i%2==0 else 9,'z':10-(i//2)*4}} for i,s in enumerate(rows)]}
@router.post('/business-cards/{id}/enter')
def enter_store(id:str,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update());b=get_business(db,id);s=db.get(BusinessSpatial,id);p=db.get(Presence,u.id);store=db.get(PublicBuilding,'store:'+id)
 if not store or not store.enabled:raise HTTPException(409,'This store has no public virtual entrance')
 if s and s.parent_building_id:
  if not p or p.zone_id!='building:'+s.parent_building_id:raise HTTPException(409,'Enter the parent mall and use its directory')
  visit=db.get(InteriorVisit,u.id)
  if not visit:raise HTTPException(409,'Re-enter the mall to restore your safe return point')
  visit.building_id=store.id;p.zone_id='building:'+store.id;p.x,p.z=entry_position(db,p.zone_id,u.id);p.mode='walk';p.updated_at=p.last_move=time.time()
 else:
  from .civic import enter
  enter(store.id,u,db)
 track(db,u,id,'store_entry');return {'ok':True}
@router.post('/business-cards/{id}/back-to-mall')
def back(id:str,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update());s=db.get(BusinessSpatial,id);p=db.get(Presence,u.id);visit=db.get(InteriorVisit,u.id)
 if not s or not s.parent_building_id or not p or p.zone_id!='building:store:'+id or not visit:raise HTTPException(409,'You are not in this mall store')
 parent=db.get(PublicBuilding,s.parent_building_id)
 if not parent or not parent.enabled:
  from .civic import exit_building
  return exit_building(db,u)
 visit.building_id=parent.id;p.zone_id='building:'+parent.id;p.x,p.z=entry_position(db,p.zone_id,u.id);p.updated_at=p.last_move=time.time();return {'ok':True}
class ProfileInput(Strict):
 description:str=Field(default='',max_length=3000)
 category:str=Field(default='',max_length=80)
 website:str=Field(default='',max_length=1200)
 opening_hours:str=Field(default='',max_length=600)
@router.put('/businesses/{id}/profile')
def update_profile(id:str,data:ProfileInput,u=Depends(current_user),db=Depends(get_db)):
 b=tenant(db,id,u,True)
 if data.website and not safe_url(data.website):raise HTTPException(422,'Enter an official HTTP or HTTPS website')
 p=db.get(BusinessSpatial,id)
 if not p:p=BusinessSpatial(business_id=id,claimed_status='claimed');db.add(p)
 b.description=data.description
 for k in ['category','website','opening_hours']:setattr(p,k,getattr(data,k))
 p.data_source='Business submitted';p.assistant_enabled=False;audit(db,u,'business.profile_updated',id);db.flush();return card(db,b)
@router.get('/businesses/{id}/spatial-analytics')
def business_metrics(id:str,u=Depends(current_user),db=Depends(get_db)):
 tenant(db,id,u)
 return {'counts':dict(db.execute(select(BusinessInteraction.kind,func.count()).where(BusinessInteraction.business_id==id).group_by(BusinessInteraction.kind)).all()),'profile':card(db,db.get(Business,id))}

class MemberInput(Strict):
 user_id:str=Field(min_length=1,max_length=36)
 enabled:bool=True
@router.put('/businesses/{id}/manager')
def manager(id:str,data:MemberInput,u=Depends(current_user),db=Depends(get_db)):
 b=db.scalar(select(Business).where(Business.id==id,Business.owner_id==u.id).with_for_update())
 if not b:raise HTTPException(403,'Only this business owner can manage its team')
 person=db.get(User,data.user_id)
 if not person or person.suspended or person.id==u.id:raise HTTPException(422,'Choose an active team member other than yourself')
 row=db.get(BusinessMember,(id,person.id))
 if data.enabled and not row:db.add(BusinessMember(business_id=id,user_id=person.id,role='BUSINESS_MANAGER'))
 if not data.enabled and row:db.delete(row)
 audit(db,u,'business.manager_added' if data.enabled else 'business.manager_removed',id);return {'ok':True}


@router.get('/super-admin/businesses')
def admin_businesses(q:str='',u=Depends(super_admin),db=Depends(get_db)):
 rows=select(Business).order_by(Business.created_at.desc())
 if q:rows=rows.where(Business.name.ilike('%'+q[:100]+'%'))
 return [{**card(db,b),'owner_id':b.owner_id} for b in db.scalars(rows.limit(100))]
