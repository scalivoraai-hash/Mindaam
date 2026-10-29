"""Bundled, attributed OSM districts; shared rendering and movement coordinates."""
import json, math, gzip, hashlib
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, HTTPException
from .locations import CITIES
router=APIRouter(prefix='/api')
@lru_cache(maxsize=64)
def terrain_position_corrections(city):
    root=Path(__file__).resolve().parents[1]/'data'
    path=root/'terrain-position-corrections.json'
    item=json.loads(path.read_text()).get(city,{}) if path.exists() else {}
    if item and item.get('map_sha256')==hashlib.sha256((root/(city+'.json.gz')).read_bytes()).hexdigest():return item
    return {}

@lru_cache(maxsize=64)
def district(city):
    if city not in {c['id'] for c in CITIES}:raise HTTPException(422,'City not enabled')
    root=Path(__file__).resolve().parents[1]/'data'
    result=json.loads(gzip.decompress((root/(city+'.json.gz')).read_bytes()))
    correction=terrain_position_corrections(city).get('spawn')
    if correction and result['spawn']==correction['old']:result['spawn']=correction['new']
    enrichment=root/'business-enrichment.json'
    if enrichment.exists():
        additions=json.loads(enrichment.read_text()).get(city,{}).get('buildings',[])
        existing={str(f['id']) for f in result['features']}
        result['features'].extend(f for f in additions if str(f['id']) not in existing)
    return result
def segment_distance(x,z,a,b):
    dx,dz=b[0]-a[0],b[1]-a[1];den=dx*dx+dz*dz
    u=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/den)) if den else 0
    return math.hypot(x-a[0]-u*dx,z-a[1]-u*dz)
@lru_cache(maxsize=64)
def road_segments(city):
    return [(a,b) for f in district(city)['features'] if 'highway' in f['tags'] and f['tags']['highway'] not in {'motorway','trunk','motorway_link'} for a,b in zip(f['points'],f['points'][1:])]
def walkable(city,x,z):
    d=district(city)
    from .grand_arena import traversable_plaza
    if traversable_plaza(city,x,z):return True
    if abs(x)>d['radius'] or abs(z)>d['radius']:return False
    from .terrain import permits
    return permits(city,x,z,buildings=False)
@router.get('/geography/{city}')
def geometry(city:str):
    from .street_vehicles import placements
    from .grand_arena import placement
    geo=district(city);arena=placement(city);radius=max(geo['radius'],max(abs(arena['x']),abs(arena['z']))+25) if arena else geo['radius']
    from .terrain import navigation
    return {**geo,'radius':radius,'navigation':navigation(city),'arena':arena,'street_vehicles':placements(city)}

@lru_cache(maxsize=64)
def footprints(city):
 return [f['points'] for f in district(city)['features'] if f['tags'].get('building') and len(f['points'])>=4]
def point_inside(x,z,points):
 inside=False
 for a,b in zip(points,points[1:]+points[:1]):
  if (a[1]>z)!=(b[1]>z) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:inside=not inside
 return inside
def inside_building(city,x,z):
 for lo_x,hi_x,lo_z,hi_z,points,holes in collision_grid(city).get((math.floor(x/32),math.floor(z/32)),[]):
  if lo_x<=x<=hi_x and lo_z<=z<=hi_z and point_inside(x,z,points) and not any(point_inside(x,z,h) for h in holes):return True
 return False
@lru_cache(maxsize=64)
def driving_segments(city):
 return [(a,b) for f in district(city)['features'] if f['tags'].get('highway') in {'residential','service','unclassified','tertiary','secondary','primary','living_street'} for a,b in zip(f['points'],f['points'][1:])]
def traversable(city,x,z,mode='walk'):
 if not walkable(city,x,z) or inside_building(city,x,z):return False
 if mode not in {'walk','run','car'}:
  from .terrain import permits
  from .grand_arena import traversable_plaza
  if not traversable_plaza(city,x,z) and not permits(city,x,z,open_ground=False):return False
 return mode!='car' or any(segment_distance(x,z,a,b)<=3.5 for a,b in street_grid(city,True).get((math.floor(x/32),math.floor(z/32)),[]))

def safe_step(city, x, z, dx, dz, mode='walk'):
    """Sweep small steps; slide on an open axis without crossing solid footprints."""
    steps=max(1,math.ceil(math.hypot(dx,dz)/.2))
    sx,sz=dx/steps,dz/steps
    for _ in range(steps):
        if traversable(city,x+sx,z+sz,mode):x,z=x+sx,z+sz
        else:
            choices=sorted([(sx,0),(0,sz)],key=lambda p:math.hypot(*p),reverse=True)
            for ax,az in choices:
                if (ax or az) and traversable(city,x+ax,z+az,mode):
                    x,z=x+ax,z+az
                    break
    return x,z

def nearest_safe_position(city,x,z,max_distance=3):
    """Recovery only for invalid positions; never moves a valid avatar for advantage."""
    if traversable(city,x,z):return x,z
    for step in range(1,int(max_distance/.25)+1):
        radius=step*.25
        for i in range(64):
            angle=i*math.tau/64
            nx,nz=x+math.cos(angle)*radius,z+math.sin(angle)*radius
            if traversable(city,nx,nz):return nx,nz
    return None

@lru_cache(maxsize=64)
def collision_grid(city):
    grid={}
    for feature in district(city)['features']:
        if not feature['tags'].get('building') or len(feature['points'])<4:continue
        polygon=feature['points'];holes=feature.get('holes',[])
        lo_x,hi_x=min(p[0] for p in polygon),max(p[0] for p in polygon)
        lo_z,hi_z=min(p[1] for p in polygon),max(p[1] for p in polygon)
        for ix in range(math.floor(lo_x/32),math.floor(hi_x/32)+1):
            for iz in range(math.floor(lo_z/32),math.floor(hi_z/32)+1):grid.setdefault((ix,iz),[]).append((lo_x,hi_x,lo_z,hi_z,polygon,holes))
    return grid

@lru_cache(maxsize=128)
def street_grid(city,driving=False):
    grid={}
    for a,b in driving_segments(city) if driving else road_segments(city):
        for ix in range(math.floor((min(a[0],b[0])-6)/32),math.floor((max(a[0],b[0])+6)/32)+1):
            for iz in range(math.floor((min(a[1],b[1])-6)/32),math.floor((max(a[1],b[1])+6)/32)+1):grid.setdefault((ix,iz),[]).append((a,b))
    return grid

@lru_cache(maxsize=64)
def safe_spawn(city):
    origin=district(city)['spawn']
    if traversable(city,*origin):return tuple(origin)
    candidates=[]
    for a,b in road_segments(city):
        length=math.hypot(b[0]-a[0],b[1]-a[1]);steps=max(1,math.ceil(length/2))
        for i in range(steps+1):
            t=i/steps;x,z=a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t
            candidates.append((math.hypot(x-origin[0],z-origin[1]),x,z))
    for _,x,z in sorted(candidates):
        if traversable(city,x,z):return x,z
    raise RuntimeError('District has no safe spawn')
