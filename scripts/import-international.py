"""One-time, cached ODbL district import for the approved international launch.

Downloads bounded extracts, never generates roads/buildings. The manifest is
written only after every district passes the shared collision/spawn checks.
Existing UK maps and production database records are not edited by this script.
"""
import ast, datetime, gzip, hashlib, importlib.util, json, math, sys, time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('osm_import',ROOT/'scripts/import-osm.py')
importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)
DATA=ROOT/'backend/data';CACHE=Path('/tmp/mylilworlds-international-osm');CACHE.mkdir(exist_ok=True)
tree=ast.parse((ROOT/'backend/api/expansion.py').read_text())
CATALOG=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='INTERNATIONAL' for t in n.targets))
INFO={id:(name,country,region) for id,name,country,region in CATALOG}

def download(row):
 id,lat,lon=row;origin={'lat':lat,'lon':lon};dx=420/(111320*math.cos(math.radians(lat)));dy=420/111320
 url=f'https://api.openstreetmap.org/api/0.6/map?bbox={lon-dx},{lat-dy},{lon+dx},{lat+dy}'
 cached=CACHE/(id+'.osm')
 if not cached.exists():
  for attempt in range(3):
   try:
    raw=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MyLilWorlds-Geography-Import/1.0','Accept':'application/xml'}),timeout=55).read()
    if b'<remark>' in raw:raise ValueError('Incomplete source result')
    cached.write_bytes(raw);break
   except Exception:
    if attempt==2:raise
    time.sleep(3)
 raw=cached.read_bytes();features=importer.convert(raw,origin)
 # Keep only features intersecting the installed district. Full source rings are
 # retained so collision and footprint geometry remain faithful to OSM.
 features=[f for f in features if min(p[0] for p in f['points'])<=430 and max(p[0] for p in f['points'])>=-430 and min(p[1] for p in f['points'])<=430 and max(p[1] for p in f['points'])>=-430]
 roads=sum('highway' in f['tags'] for f in features);buildings=sum('building' in f['tags'] for f in features)
 if roads<5 or buildings<1:raise ValueError(f'{id}: insufficient mapped streets/buildings')
 d={'city':id,'district':'Central district','origin':origin,'radius':350,'spawn':[0,0],'features':features,'source':'OpenStreetMap contributors','source_url':'https://www.openstreetmap.org/copyright','license':'ODbL 1.0','retrieved':datetime.date.today().isoformat(),'source_sha256':hashlib.sha256(raw).hexdigest(),'extract_bbox':[lon-dx,lat-dy,lon+dx,lat+dy]}
 (DATA/(id+'.json.gz')).write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
 print(id,roads,'roads',buildings,'buildings',flush=True)
 return {'id':id,'roads':roads,'buildings':buildings,'features':len(features),'source_sha256':d['source_sha256']}

def main():
 rows=json.loads((DATA/'international-launch.json').read_text())
 with ThreadPoolExecutor(max_workers=2) as pool:audits=list(pool.map(download,rows))
 from backend.api import locations,geography
 manifest=[]
 for row in rows:
  id=row[0];name,country,region=INFO[id]
  if id not in {c['id'] for c in locations.CITIES}:locations.CITIES.append({'id':id,'name':name,'zone':'Central district','country':country,'region':region})
  d=json.loads(gzip.decompress((DATA/(id+'.json.gz')).read_bytes()))
  d['spawn']=list(geography.safe_spawn(id));assert geography.traversable(id,*d['spawn'])
  (DATA/(id+'.json.gz')).write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
  manifest.append({'id':id,'name':name,'country':country,'region':region,'zone':'Central district','reviewed':True,'source':d['source'],'license':d['license'],'launch_active':True})
  next(a for a in audits if a['id']==id)['safe_spawn']=d['spawn']
 (DATA/'world-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (DATA/'international-import-audit.json').write_text(json.dumps({'scope':'28 source-backed bounded central districts; not whole-city coverage or surveyed interiors','attribution':'© OpenStreetMap contributors · ODbL 1.0','retrieved':datetime.date.today().isoformat(),'districts':audits},indent=2)+'\n')
 print('Validated all 28 launch districts',flush=True)
if __name__=='__main__':main()
