"""Read-only coverage evidence from the existing staging migration job."""
import json,os,subprocess,time
from pathlib import Path

PROBE = '''import os,json
from sqlalchemy.engine import make_url
assert os.environ.get('APP_ENV')=='staging'
url=make_url(os.environ['RUNTIME_DATABASE_URL'])
assert (url.username,url.database)==('mindaam_staging','mindaam_staging')
os.environ['DATABASE_URL']=os.environ['RUNTIME_DATABASE_URL']
from sqlalchemy import select,text
from backend.api.db import SessionLocal
from backend.api.discovery import catalog
from backend.api.expansion import Destination
from backend.api.property_inventory import inventory
from backend.api.property_economy import Property,Price,pricing
report=[]
with SessionLocal() as db:
 db.execute(text('SET TRANSACTION READ ONLY'))
 assert tuple(db.execute(text('SELECT current_database(),current_user')).one())==('mindaam_staging','mindaam_staging')
 destinations={c.id:c for c in db.scalars(select(Destination))}
 rules={(r.scope,r.category):r for r in db.scalars(select(Price))}
 for city in catalog(db):
  if not all(city.get(k) for k in ('enabled','public','joinable')):continue
  city=city['id'];mapped=inventory(city)
  registered={p.id:p for p in db.scalars(select(Property).where(Property.city==city))}
  missing=set(mapped)-set(registered);geometry=[];prices=[];available=owned=enabled=venues=0
  for key,shape in mapped.items():
   p=registered.get(key)
   if p is None:continue
   if (p.x,p.z,p.category)!=(shape['x'],shape['z'],shape['category']):geometry.append(key)
   xp,allowed=pricing(db,p,rules)
   if p.category=='venue':venues+=1;continue
   prices.append(xp);owned+=int(p.owner is not None);enabled+=int(allowed);available+=int(allowed and p.owner is None)
  report.append({'city':city,'mapped_buildings':sum(p['category']!='venue' for p in mapped.values()),'registered':len(registered),'venue_records':venues,'owned_buildings':owned,'available_buildings':available,'enabled_buildings':enabled,'minimum_xp':min(prices) if prices else None,'maximum_xp':max(prices) if prices else None,'missing_count':len(missing),'geometry_mismatches':len(geometry),'valid_prices':bool(prices) and all(isinstance(x,int) and x>0 for x in prices)})
print('MINDAAM_PROPERTY_COVERAGE '+json.dumps({'read_only':True,'cities':report},sort_keys=True))
'''

def run():
    release=json.loads(Path('deployment-result.json').read_text())
    if release.get('environment')!='staging' or release.get('origin')!='https://mindaam-staging-qfrofqn4pq-nw.a.run.app' or release.get('sha')!=os.environ.get('RELEASE_SHA') or os.environ.get('MINDAAM_PROJECT_ID')!='mindaam':
        raise RuntimeError('Exact existing staging release required')
    execution=json.loads(subprocess.check_output(['gcloud','run','jobs','execute','mindaam-migrate-staging','--project=mindaam','--region=europe-west2','--wait','--format=json','--args=^~^-c~'+PROBE],text=True))['metadata']['name']
    query='resource.type="cloud_run_job" AND labels."run.googleapis.com/execution_name"="'+execution+'" AND textPayload:"MINDAAM_PROPERTY_COVERAGE "'
    rows=[]
    for attempt in range(12):
        rows=json.loads(subprocess.check_output(['gcloud','logging','read',query,'--project=mindaam','--limit=5','--format=json'],text=True))
        if rows:break
        time.sleep(5)
    if len(rows)!=1:raise RuntimeError('Unique property coverage evidence unavailable')
    result=json.loads(rows[0]['textPayload'].split('MINDAAM_PROPERTY_COVERAGE ',1)[1])
    result.update(sha=release['sha'],image=release['image'],revision=release['revision'],execution=execution)
    Path('gcp-evidence').mkdir(exist_ok=True)
    Path('gcp-evidence/property-coverage.json').write_text(json.dumps(result,indent=2))
    cities=result['cities']
    if not cities or any(c['missing_count'] or c['geometry_mismatches'] or not c['valid_prices'] for c in cities):
        raise RuntimeError('Active-city property coverage has unresolved gaps; inspect property-coverage.json')
    print('Read-only staging coverage verified:',len(cities),'active cities;',sum(c['mapped_buildings'] for c in cities),'mapped buildings;',sum(c['registered'] for c in cities),'registered records')

if __name__=='__main__':run()
