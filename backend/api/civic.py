"""Public interiors extend virtual Presence; no access to private residences."""
import time,math
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import String,Float,Boolean,ForeignKey,select
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base,get_db
from .models import Presence,User,Session,Audit
from .auth import current_user
from .core import serialize
from .geography import district,road_segments,point_inside,traversable,safe_spawn,street_grid
from .growth import require_access
router=APIRouter(prefix='/api/buildings')
PUBLIC={'library':'library','community_centre':'community','place_of_worship':'worship','townhall':'reception','arts_centre':'museum','museum':'museum','restaurant':'cafe','cafe':'cafe','public_bookcase':'library','train_station':'station'}
class PublicBuilding(Base):
 __tablename__='public_buildings'
 id:Mapped[str]=mapped_column(String(100),primary_key=True)
 city:Mapped[str]=mapped_column(String(50),index=True)
 name:Mapped[str]=mapped_column(String(160))
 template:Mapped[str]=mapped_column(String(30))
 source_id:Mapped[str]=mapped_column(String(80))
 x:Mapped[float]=mapped_column(Float)
 z:Mapped[float]=mapped_column(Float)
 enabled:Mapped[bool]=mapped_column(Boolean,default=True)
class InteriorVisit(Base):
 __tablename__='building_visits'
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
 building_id:Mapped[str]=mapped_column(ForeignKey('public_buildings.id'))
 return_x:Mapped[float]=mapped_column(Float)
 return_z:Mapped[float]=mapped_column(Float)
 created_at:Mapped[float]=mapped_column(Float,default=time.time)

def entrance(city,point):
 # Bound candidate roads to nearby cells; avoid scanning a whole city for each shop.
 grid=street_grid(city);near={}
 for ix in range(math.floor((point[0]-65)/32),math.floor((point[0]+65)/32)+1):
  for iz in range(math.floor((point[1]-65)/32),math.floor((point[1]+65)/32)+1):
   for a,b in grid.get((ix,iz),[]):near[(tuple(a),tuple(b))]=(a,b)
 candidates=[]
 for a,b in near.values():
  dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz);t=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dz)/(length*length or 1)));x,z=a[0]+t*dx,a[1]+t*dz
  if math.hypot(x-point[0],z-point[1])>=65:continue
  # Prefer a walkable shoulder over the middle of a drivable roadway.
  for side in [-1,1,0]:
   px,pz=x-dz/(length or 1)*4.5*side,z+dx/(length or 1)*4.5*side
   candidates.append((math.hypot(px-point[0],pz-point[1]),px,pz))
 # Preserve nearest walkable-shoulder preference, but stop checking geometry as
 # soon as that best candidate is known. Global catalogue bootstrap must not
 # exhaustively collide every candidate for every source-backed shop.
 fallback=None
 for _,x,z in sorted(candidates):
  if not traversable(city,x,z):continue
  if not traversable(city,x,z,'car'):return x,z
  if fallback is None:fallback=(x,z)
 return fallback

def seed_buildings(db):
 from .locations import CITIES
 existing=set(db.scalars(select(PublicBuilding.id)))
 for city in CITIES:
  for f in district(city['id'])['features']:
   tags=f['tags'];kind=tags.get('amenity') or tags.get('tourism') or tags.get('railway')
   if kind not in PUBLIC or not tags.get('name') or tags.get('access') in ['private','no','customers','permit'] or tags.get('building') in ['house','apartments','residential','detached','terrace']:continue
   id=city['id']+':'+str(f['id'])
   if id in existing:continue
   pts=f['points'];point=[sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts)];entry=entrance(city['id'],point)
   if not entry:continue
   db.add(PublicBuilding(id=id,city=city['id'],name=tags['name'][:160],template=PUBLIC[kind],source_id=str(f['id']),x=entry[0],z=entry[1]));existing.add(id)
 db.flush()

def active_inside(db,id):
 alive=select(Session.user_id).where(Session.expires_at>time.time())
 return list(db.scalars(select(Presence).join(User,User.id==Presence.user_id).where(Presence.zone_id=='building:'+id,Presence.updated_at>time.time()-45,User.suspended==False,User.id.in_(alive))))

def entry_position(db,zone,user_id,stage=False):
 """Separate arriving real avatars; venue row locks serialize entry decisions."""
 occupied=list(db.execute(select(Presence.x,Presence.z).where(Presence.zone_id==zone,Presence.user_id!=user_id,Presence.updated_at>time.time()-45)))
 if stage:candidates=[(x,-10) for x in [0,-2.2,2.2,-4.4,4.4,-6.6,6.6,-8.8,8.8]]
 else:candidates=[(x,z) for z in [8,5.5,3,.5,-2,10.5,13] for x in [0,-2.2,2.2,-4.4,4.4,-6.6,6.6,-8.8,8.8]]
 return next((point for point in candidates if all(math.dist(point,other)>1.25 for other in occupied)),candidates[sum(map(ord,user_id))%len(candidates)])
def listing(db,city,x=None,z=None):
 from sqlalchemy import func
 from .business_spatial import BusinessSpatial
 inside_ids=select('store:'+BusinessSpatial.business_id).where(BusinessSpatial.parent_building_id!=None)
 query=select(PublicBuilding).where(PublicBuilding.city==city,PublicBuilding.enabled==True,~PublicBuilding.id.in_(inside_ids))
 if x is not None and z is not None:query=query.where(PublicBuilding.x.between(x-110,x+110),PublicBuilding.z.between(z-110,z+110)).order_by((PublicBuilding.x-x)*(PublicBuilding.x-x)+(PublicBuilding.z-z)*(PublicBuilding.z-z))
 alive=select(Session.user_id).where(Session.expires_at>time.time())
 counts=dict(db.execute(select(Presence.zone_id,func.count()).join(User,User.id==Presence.user_id).where(Presence.city==city,Presence.zone_id.like('building:%'),Presence.updated_at>time.time()-45,User.suspended==False,User.id.in_(alive)).group_by(Presence.zone_id)).all())
 return [{**serialize(b),'inside':counts.get('building:'+b.id,0)} for b in db.scalars(query.limit(24))]
@router.get('/city/{city}')
def buildings(city:str,u=Depends(current_user),db=Depends(get_db)):return listing(db,city)
@router.post('/{id}/enter')
def enter(id:str,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update());b=db.scalar(select(PublicBuilding).where(PublicBuilding.id==id).with_for_update());p=db.get(Presence,u.id)
 if not b or not b.enabled:raise HTTPException(404,'This property is not open to visitors')
 require_access(db,u,b.city)
 from .mobility import current
 if current(db,u):raise HTTPException(409,'Exit your rental first')
 if not p or p.city!=b.city or p.zone_id!='world' or math.hypot(p.x-b.x,p.z-b.z)>10:raise HTTPException(409,'Approach the public entrance first')
 if db.get(InteriorVisit,u.id):raise HTTPException(409,'Exit your current building first')
 db.add(InteriorVisit(user_id=u.id,building_id=b.id,return_x=p.x,return_z=p.z));p.zone_id='building:'+id;p.x,p.z=entry_position(db,p.zone_id,u.id);p.mode='walk';p.last_move=time.time();p.updated_at=time.time()
 db.add(Audit(actor_id=u.id,action='building.enter',target=id));return {'ok':True}
def exit_building(db,u):
 """Unconditional, idempotent escape, including expired presence and closed venues."""
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 visit=db.get(InteriorVisit,u.id);p=db.get(Presence,u.id)
 if not visit and (not p or not p.zone_id.startswith('building:')):
  return {'city':p.city if p else u.city,'position':{'x':p.x,'z':p.z,'mode':p.mode,'zone_id':p.zone_id,'last_move':p.last_move} if p else None}
 b=db.get(PublicBuilding,visit.building_id if visit else p.zone_id[9:])
 city=b.city if b else p.city if p else u.city
 if visit and traversable(city,visit.return_x,visit.return_z):point=(visit.return_x,visit.return_z) if not traversable(city,visit.return_x,visit.return_z,'car') else entrance(city,(visit.return_x,visit.return_z)) or (visit.return_x,visit.return_z)
 elif b and traversable(city,b.x,b.z):point=(b.x,b.z)
 else:point=safe_spawn(city)
 if not p:p=Presence(user_id=u.id,city=city);db.add(p)
 p.city=city;p.zone_id='world';p.x,p.z=point;p.mode='walk';p.return_position={};p.last_move=time.time();p.updated_at=time.time();u.city=city
 if visit:db.delete(visit)
 db.add(Audit(actor_id=u.id,action='building.exit',target=b.id if b else 'recovery'))
 return {'city':city,'position':{'x':p.x,'z':p.z,'mode':p.mode,'zone_id':'world','last_move':p.last_move}}

@router.post('/exit')
def leave(u=Depends(current_user),db=Depends(get_db)):return exit_building(db,u)

def restore_visit(db,u,city):
 visit=db.get(InteriorVisit,u.id)
 if not visit:return
 b=db.get(PublicBuilding,visit.building_id);p=db.get(Presence,u.id)
 if not b or not b.enabled:
  exit_building(db,u);return
 if b.city!=city:
  # Explicit world selection may resume after presence expired in another interior.
  # Recover its saved exterior first; world/enter has already checked destination access.
  exit_building(db,u);return
 if not p:
  x,z=entry_position(db,'building:'+b.id,u.id);db.add(Presence(user_id=u.id,city=b.city,zone_id='building:'+b.id,x=x,z=z,mode='walk'));db.flush()
 elif p.zone_id=='world':
  # Presence may have been recreated after expiry. Retire the stale visit safely.
  exit_building(db,u)

def scene(db,p):
 if not p.zone_id.startswith('building:'):return None
 b=db.get(PublicBuilding,p.zone_id[9:])
 if not b or not b.enabled:
  exit_building(db,db.get(User,p.user_id));return None
 # One reused world renderer, clearly labelled configurable interiors; no claim of survey accuracy.
 from .business_spatial import BusinessSpatial,card
 from .commerce import Business
 tenants=list(db.scalars(select(BusinessSpatial).where(BusinessSpatial.parent_building_id==b.id).order_by(BusinessSpatial.business_id))) if b.template=='mall' else []
 back=min(-15,6-((len(tenants)+1)//2)*4) if tenants else -15
 profile=db.get(BusinessSpatial,b.id[6:]) if b.id.startswith('store:') else None
 return {'back':back,'parent_building_id':profile.parent_building_id if profile else None,'shops':[{**card(db,db.get(Business,t.business_id)),'door':{'x':-9 if i%2==0 else 9,'z':10-(i//2)*4}} for i,t in enumerate(tenants)],'id':b.id,'name':b.name,'template':b.template,'notice':'Real-world-inspired interior template. Not a surveyed interior.','geography':{'city':b.city,'radius':max(35,abs(back)+20),'spawn':[0,8],'features':[{'id':str(i+900000),'tags':{'building':'yes','height':'5'},'points':pts} for i,pts in enumerate([[[-12,back-1],[12,back-1],[12,back],[-12,back],[-12,back-1]],[[-12,15],[-2,15],[-2,16],[-12,16],[-12,15]],[[2,15],[12,15],[12,16],[2,16],[2,15]],[[-12,back-1],[-11,back-1],[-11,16],[-12,16],[-12,back-1]],[[11,back-1],[12,back-1],[12,16],[11,16],[11,back-1]]])]},'inside':len(active_inside(db,b.id))}
