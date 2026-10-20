"""Shared trail provisioning. Existing authored trails and every claim stay intact."""
import hashlib,json,math
from functools import lru_cache
from collections import deque
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
from sqlalchemy import select
from .geography import district,safe_spawn,traversable,safe_step,point_inside,segment_distance
from .models import Collectible,Mission
from .economy import config

ROOT=Path(__file__).resolve().parents[1]/'data'
DEFAULTS={'count':48,'overrides':{}}

@lru_cache(maxsize=64)
def exclusion_grid(city):
    grid={}
    for f in district(city)['features']:
        t=f['tags'];points=f['points']
        private=t.get('access') in ['private','no']
        area=len(points)>=4 and points[0]==points[-1] and (t.get('natural')=='water' or t.get('waterway')=='riverbank' or private)
        line=private and t.get('highway')
        if not area and not line:continue
        margin=1.5 if line else 0
        for ix in range(math.floor((min(p[0] for p in points)-margin)/32),math.floor((max(p[0] for p in points)+margin)/32)+1):
            for iz in range(math.floor((min(p[1] for p in points)-margin)/32),math.floor((max(p[1] for p in points)+margin)/32)+1):
                grid.setdefault((ix,iz),[]).append((f,area,line))
    return grid

def excluded(city,x,z):
    for f,area,line in exclusion_grid(city).get((math.floor(x/32),math.floor(z/32)),[]):
        if area and point_inside(x,z,f['points']) and not any(point_inside(x,z,h) for h in f.get('holes',[])):return True
        if line and any(segment_distance(x,z,a,b)<1.5 for a,b in zip(f['points'],f['points'][1:])):return True
    return False

def trail_points(city,count=48,step=4):
    """Follow existing traversable paths; choose spaced, off-carriageway items."""
    spawn=safe_spawn(city)
    queue=deque([(0,0)]);seen={(0,0)};candidates=[]
    d=district(city)
    while queue:
        ix,iz=queue.popleft();x,z=spawn[0]+ix*step,spawn[1]+iz*step
        if not traversable(city,x,z,'car') and not excluded(city,x,z):
            candidates.append((x,z))
        for ox,oz in [(1,0),(-1,0),(0,1),(0,-1)]:
            key=(ix+ox,iz+oz)
            if key in seen:continue
            nx,nz=spawn[0]+key[0]*step,spawn[1]+key[1]*step
            if abs(nx)>d['radius'] or abs(nz)>d['radius']:seen.add(key);continue
            if not traversable(city,nx,nz):seen.add(key);continue
            # Endpoint-only checks can jump through a narrow wall. Verify segment.
            end=safe_step(city,x,z,ox*step,oz*step)
            if math.dist(end,(nx,nz))>.01:continue
            seen.add(key);queue.append(key)
    if len(candidates)<count and step>2:return trail_points(city,count,2)
    if len(candidates)<12:raise RuntimeError('Insufficient reachable public trail points: '+city)
    # Farthest-point sampling spreads rewards through the connected neighbourhood.
    first=min(candidates,key=lambda p:math.dist(p,spawn))
    chosen=[first];remaining=[(p,math.dist(p,first)) for p in candidates if p!=first]
    while remaining and len(chosen)<count:
        point,spacing=max(remaining,key=lambda q:q[1])
        if spacing<5:break
        chosen.append(point)
        remaining=[(p,min(distance,math.dist(p,point))) for p,distance in remaining if p!=point]
    return chosen

@lru_cache(maxsize=128)
def prepared_points(city,count):
    cache=ROOT/'world-trails.json'
    item=json.loads(cache.read_text()).get(city) if cache.exists() else None
    checksum=hashlib.sha256((ROOT/(city+'.json.gz')).read_bytes()).hexdigest()
    # A small district may exhaust its safe positions before the requested count.
    # Preserve that complete result instead of regenerating it on every cold load.
    if item and item.get('version')==3 and item['map_sha256']==checksum and (len(item['points'])>=count or item.get('prepared_count',0)>=count):
        return item['points'][:count]
    return trail_points(city,count)

def seed_world(db,city,name):
    # One lock shared by startup and admin activation; no duplicate item grants.
    from .expansion import Destination
    db.scalar(select(Destination).where(Destination.id==city).with_for_update())
    if not db.scalar(select(Collectible.id).where(Collectible.city==city).limit(1)):
        settings=config(db,'world_trails',DEFAULTS)
        count=max(12,min(96,int(settings.get('overrides',{}).get(city,settings.get('count',48)))))
        for index,(x,z) in enumerate(prepared_points(city,count)):
            kind='gem' if index%4==3 else 'fruit'
            title='Crystal' if kind=='gem' else ['Apple','Orange','Bananas'][index%3]
            db.add(Collectible(id=str(uuid5(NAMESPACE_URL,f'mylilworlds:trail:{city}:{index}')),city=city,title=title,kind=kind,x=x,z=z))
    if not db.scalar(select(Mission.id).where(Mission.city==city).limit(1)):
        db.add(Mission(id=str(uuid5(NAMESPACE_URL,'mylilworlds:mission:'+city)),city=city,title='Explore '+name,description='Follow the public paths. Collect 3 fruit and 1 crystal.',requirements={'fruit':3,'gem':1},credits=30,xp=50))
    db.flush()

def seed_active(db):
    from .expansion import Destination
    from .locations import CITIES
    installed={c['id'] for c in CITIES}
    for d in db.scalars(select(Destination).where(Destination.status=='ACTIVE',Destination.public==True,Destination.joinable==True)):
        if d.id in installed:seed_world(db,d.id,d.name)
