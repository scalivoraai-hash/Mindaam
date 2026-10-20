"""Prepare deterministic, collision-checked trails from the installed OSM maps."""
import hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.api.world_content import ROOT,trail_points
from backend.api.locations import CITIES
path=ROOT/'world-trails.json'
cache=json.loads(path.read_text()) if path.exists() else {}
for city in CITIES:
 # Cache preparation never changes database collectibles or their claim history.
 # UK rotations also require current caches; skipping them makes live snapshots
 # synchronously regenerate a whole district's trail on the first request.
 id=city['id'];checksum=hashlib.sha256((ROOT/(id+'.json.gz')).read_bytes()).hexdigest()
 item=cache.get(id,{})
 if item.get('version')==3 and item.get('map_sha256')==checksum and (len(item.get('points',[]))>=96 or item.get('prepared_count',0)>=96):continue
 start=time.monotonic();points=trail_points(id,96)
 cache[id]={'version':3,'map_sha256':checksum,'prepared_count':96,'points':points}
 path.write_text(json.dumps(cache,indent=2)+'\n')
 print(id,len(points),round(time.monotonic()-start,2),flush=True)
