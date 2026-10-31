"""Bounded billboard footprint validation against the existing city geometry."""
import math
from functools import lru_cache
from .geography import district,segment_distance
from .terrain import permits

@lru_cache(maxsize=64)
def road_grid(city):
 result={}
 for feature in district(city)['features']:
  if not feature['tags'].get('highway'):continue
  for a,b in zip(feature['points'],feature['points'][1:]):
   for ix in range(math.floor((min(a[0],b[0])-10)/32),math.floor((max(a[0],b[0])+10)/32)+1):
    for iz in range(math.floor((min(a[1],b[1])-10)/32),math.floor((max(a[1],b[1])+10)/32)+1):result.setdefault((ix,iz),[]).append((a,b))
 return result

def safe(city,x,z):
 if not math.isfinite(x) or not math.isfinite(z):return False
 # Includes clearance around the board's posts and width, not just its centre.
 if not all(permits(city,x+dx,z+dz) for dx in [-4,0,4] for dz in [-4,0,4]):return False
 return all(segment_distance(x,z,a,b)>=10 for a,b in road_grid(city).get((math.floor(x/32),math.floor(z/32)),[]))

@lru_cache(maxsize=64)
def initial_points(city):
 from .world_content import prepared_points
 from .geography import safe_step
 candidates=[]
 for x,z in prepared_points(city,48):
  for dx,dz in [(0,0)]+[(r*dx,r*dz) for r in [8,12,20,32,48] for dx,dz in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)]]:
   px,pz=x+dx,z+dz
   if safe(city,px,pz) and math.dist(safe_step(city,x,z,dx,dz),(px,pz))<.01:candidates.append((px,pz))
 if len(candidates)<3 or max((math.dist(a,b) for a in candidates for b in candidates),default=0)<120:
  # Dense legacy trail caches can cover only the spawn block. Search bounded
  # public ground without changing the city or weakening footprint checks.
  radius=int(district(city)['radius'])
  candidates.extend((x,z) for x in range(-radius+10,radius-10,16) for z in range(-radius+10,radius-10,16) if safe(city,x,z))
 if not candidates:return []
 chosen=[max(candidates,key=lambda p:math.dist(p,candidates[0]))]
 for _ in range(2):
  next_point=max(candidates,key=lambda p:min(math.dist(p,q) for q in chosen))
  if min(math.dist(next_point,q) for q in chosen)<60:return []
  chosen.append(next_point)
 return chosen

@lru_cache(maxsize=64)
def prepared_placements(city):
 import json,hashlib
 from pathlib import Path
 root=Path(__file__).resolve().parents[1]/'data'
 item=json.loads((root/'billboard-placements.json').read_text()).get(city,{})
 if item.get('map_sha256')!=hashlib.sha256((root/(city+'.json.gz')).read_bytes()).hexdigest():return []
 points=item.get('points',[])
 if len(points)!=3 or not all(safe(city,*p) for p in points):return []
 if any(math.dist(a,b)<60 for i,a in enumerate(points) for b in points[i+1:]):return []
 return points
