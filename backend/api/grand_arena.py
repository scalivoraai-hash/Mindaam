"""One deterministic shared landmark per installed city, using existing event rooms."""
import math,time,json,hashlib
from pathlib import Path
from functools import lru_cache
from sqlalchemy import select
from .geography import district,segment_distance,point_inside

@lru_cache(maxsize=1)
def precomputed():
 path=Path(__file__).resolve().parents[1]/'data/arena-placements.json'
 return json.loads(path.read_text()) if path.exists() else {}

@lru_cache(maxsize=128)
def placement(city):
 root=Path(__file__).resolve().parents[1]/'data'
 saved=precomputed().get(city)
 if saved:
  enrichment=root/'business-enrichment.json'
  digest=hashlib.sha256((root/(city+'.json.gz')).read_bytes()+(enrichment.read_bytes() if enrichment.exists() else b'')+(root/'world-trails.json').read_bytes()).hexdigest()
  if saved.get('source_hash')==digest:return {k:v for k,v in saved.items() if k!='source_hash'}
 geo=district(city);features=geo['features'];spawn=geo['spawn'];half=13
 obstacles=[];polygons=[];roads=[]
 collectibles=json.loads((root/'world-trails.json').read_text()).get(city,{}).get('points',[])
 for f in features:
  tags=f['tags'];points=f['points']
  if tags.get('building') or tags.get('natural')=='water' or tags.get('waterway') or (tags.get('name') and not tags.get('highway')):
   polygons.append(points)
   obstacles.append((min(p[0] for p in points),max(p[0] for p in points),min(p[1] for p in points),max(p[1] for p in points)))
  if tags.get('highway') and tags['highway'] not in {'motorway','trunk','motorway_link','steps'}:
   roads.extend(zip(points,points[1:]))
 def solid(x,z,radius):
  if radius>=10 and any(math.hypot(x-p[0],z-p[1])<radius+3 for p in collectibles):return True
  for (lo,hi,low,high),points in zip(obstacles,polygons):
   if lo<x+radius and hi>x-radius and low<z+radius and high>z-radius:
    if point_inside(x,z,points) or any(segment_distance(x,z,a,b)<=radius for a,b in zip(points,points[1:]+points[:1])):return True
  return False
 roads.sort(key=lambda pair:math.hypot((pair[0][0]+pair[1][0])/2-spawn[0],(pair[0][1]+pair[1][1])/2-spawn[1]))
 for a,b in roads:
  length=math.dist(a,b)
  if length<8:continue
  nx,nz=(b[1]-a[1])/length,-(b[0]-a[0])/length
  for frac in (.5,.25,.75):
   px,pz=a[0]+(b[0]-a[0])*frac,a[1]+(b[1]-a[1])*frac
   for sign in (-1,1):
    x,z=px+nx*sign*24,pz+nz*sign*24
    if max(abs(x),abs(z))+half>geo['radius']:continue
    if solid(x,z,20):continue
    # Conservative circle clearance keeps all footprint corners outside mapped roads.
    if any(segment_distance(x,z,c,d)<half*math.sqrt(2)+4 for c,d in roads):continue
    entrance=[px+nx*sign*6,pz+nz*sign*6]
    # The short entry path must also be clear of buildings and water.
    if any(solid(entrance[0]+(x-entrance[0])*step/30,entrance[1]+(z-entrance[1])*step/30,2) for step in range(31)):continue
    return {'id':'grand-arena:'+city,'name':'Mindaam Grand Arena','x':x,'z':z,'half':half,'entrance':entrance,'heading':math.atan2(-nx*sign,-nz*sign),'version':1}
 # Dense mapped centres may have no vacant plot. Extend a clear pedestrian spur
 # from an existing road into a dedicated plaza outside the mapped district.
 anchors=sorted({(p[0],p[1]) for a,b in roads for p in [a,b,[(a[0]+b[0])/2,(a[1]+b[1])/2]] if max(abs(p[0]),abs(p[1]))<geo['radius']},key=lambda p:-math.hypot(*p))
 for px,pz in anchors:
  length=math.hypot(px,pz)
  if not length:continue
  outward=(px/length,pz/length)
  for angle in [0,.25,-.25,.5,-.5]:
   nx=outward[0]*math.cos(angle)-outward[1]*math.sin(angle);nz=outward[0]*math.sin(angle)+outward[1]*math.cos(angle)
   for reach in [55,80,110,160,240]:
    x,z=px+nx*reach,pz+nz*reach
    if solid(x,z,20):continue
    if any(segment_distance(x,z,c,d)<half*math.sqrt(2)+4 for c,d in roads):continue
    end=[x-nx*12,z-nz*12]
    steps=math.ceil(math.dist([px,pz],end))
    if any(solid(px+(end[0]-px)*step/steps,pz+(end[1]-pz)*step/steps,2) for step in range(steps+1)):continue
    return {'id':'grand-arena:'+city,'name':'Mindaam Grand Arena','x':x,'z':z,'half':half,'entrance':[px,pz],'heading':math.atan2(-nx,-nz),'version':1,'extended_plaza':True}
 return None

def traversable_plaza(city,x,z):
 arena=placement(city)
 if not arena:return False
 # The exterior's solid footprint is not traversable; the entrance plaza connects to the road.
 ex,ez=arena['entrance'];dx,dz=x-arena['x'],z-arena['z'];c,s=math.cos(arena['heading']),math.sin(arena['heading'])
 local_x,local_z=c*dx-s*dz,s*dx+c*dz
 return abs(local_x)<=13 and 8<=local_z<=14 or segment_distance(x,z,[ex,ez],[arena['x']+s*12,arena['z']+c*12])<=2

def view(db,city,user):
 arena=placement(city)
 if not arena:return None
 from .models import Event,User
 from .events import visible
 from .venue_rentals import booking
 from .event_tickets import summary
 now=time.time();items=[]
 for e in db.scalars(select(Event).where(Event.city==city,Event.venue_experience_type=='auditorium',Event.status.in_(['scheduled','live']),((Event.starts_at>now-14400)|(Event.ends_at>now))).order_by(Event.starts_at).limit(12)):
  if not visible(db,e,user):continue
  if (e.programme or {}).get('arena_booking_required') and not booking(db,e.id):continue
  host=db.get(User,e.host_id)
  items.append({'id':e.id,'title':e.title,'host':host.username if host else 'Organiser','starts_at':e.starts_at,'status':e.status,'visibility':e.visibility,'ticket_price':e.ticket_price,'available':summary(db,e,user)['available'],'cover_image':(e.programme or {}).get('cover_image','')})
 return {**arena,'events':items[:5]}

# Event billboards refresh separately from high-frequency movement snapshots.
from fastapi import APIRouter,Depends
from .auth import current_user
from .db import get_db
router=APIRouter(prefix='/api/arenas')
@router.get('/{city}')
def detail(city:str,u=Depends(current_user),db=Depends(get_db)):
 from .core import check_city
 check_city(city)
 return view(db,city,u)
