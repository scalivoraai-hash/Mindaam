"""Import bounded licensed OSM XML extracts; excludes private address tags.
Usage: python scripts/import-osm.py --cities | --whitehouse /path/to/export.osm
No runtime dependency on the source API. Existing world/reward objects are untouched.
"""
import argparse,gzip,json,math,sys,hashlib,datetime,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.api.locations import CITIES
DATA=ROOT/'backend/data'
TAGS={'building','building:levels','height','name','highway','natural','leisure','amenity','shop','entrance','surface','access'}
def inside(p,ring):
 x,y=p;result=False
 for a,b in zip(ring,ring[1:]+ring[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:result=not result
 return result

def rings(parts):
 parts=[list(p) for p in parts if len(p)>1];result=[]
 while parts:
  chain=parts.pop()
  while chain[-1]!=chain[0]:
   match=next(((i,p) for i,p in enumerate(parts) if chain[-1] in [p[0],p[-1]]),None)
   if not match:break
   i,p=match;parts.pop(i);chain.extend((p if p[0]==chain[-1] else p[::-1])[1:])
  if chain[0]==chain[-1] and len(chain)>=4:result.append(chain)
 return result

def convert(raw,origin):
 root=ET.fromstring(raw);nodes={n.attrib['id']:n for n in root.findall('node')};ways={w.attrib['id']:w for w in root.findall('way')};features=[];used=set()
 def tags(e):return {t.attrib['k']:t.attrib['v'] for t in e.findall('tag') if t.attrib['k'] in TAGS}
 def point(id):
  n=nodes[id];return [round((float(n.attrib['lon'])-origin['lon'])*111320*math.cos(math.radians(origin['lat'])),2),round((origin['lat']-float(n.attrib['lat']))*111320,2)]
 def refs(w):return [n.attrib['ref'] for n in w.findall('nd')]
 for rel in root.findall('relation'):
  t=tags(rel)
  if not any(k in t for k in ['building','natural','leisure']):continue
  members=[m for m in rel.findall('member') if m.attrib['type']=='way'];outer=[refs(ways[m.attrib['ref']]) for m in members if m.attrib.get('role','outer') in ['','outer'] and m.attrib['ref'] in ways];inner=[refs(ways[m.attrib['ref']]) for m in members if m.attrib.get('role')=='inner' and m.attrib['ref'] in ways]
  outs=rings(outer);ins=rings(inner)
  for i,ring in enumerate(outs):
   if not all(id in nodes for id in ring):continue
   pts=[point(id) for id in ring];holes=[[point(id) for id in h] for h in ins if all(id in nodes for id in h) and inside(point(h[0]),pts)]
   features.append({'id':str(1000000000000+int(rel.attrib['id'])*100+i),'osm_type':'relation','osm_id':rel.attrib['id'],'tags':t,'points':pts,'holes':holes,'source_way_ids':[m.attrib['ref'] for m in members if m.attrib['ref'] in ways and set(refs(ways[m.attrib['ref']])).issubset(set(ring))]})
   used.update(m.attrib['ref'] for m in members if m.attrib.get('role','outer') in ['','outer'] and m.attrib['ref'] in ways and set(refs(ways[m.attrib['ref']])).issubset(set(ring)))
 for id,w in ways.items():
  t=tags(w);ids=refs(w)
  if id in used or not any(k in t for k in ['building','highway','natural','leisure','shop','amenity']) or not all(i in nodes for i in ids):continue
  if 'building' in t and (len(ids)<4 or ids[0]!=ids[-1]):continue
  if len(ids)>=2:features.append({'id':id,'tags':t,'points':[point(i) for i in ids]})
 for id,n in nodes.items():
  t=tags(n)
  if t.get('name') and any(k in t for k in ['shop','amenity']):features.append({'id':str(2000000000000+int(id)),'osm_type':'node','osm_id':id,'tags':t,'points':[point(id)]})
 return features

def save(city,raw,old=None):
 spec=next(c for c in CITIES if c['id']==city);origin=old['origin'] if old else spec['origin'];fresh=convert(raw,origin)
 if old:
  covered={id for f in fresh for id in f.get('source_way_ids',[])};merged={str(f['id']):f for f in old['features'] if str(f['id']) not in covered};merged.update({f['id']:f for f in fresh});d={**old,'features':list(merged.values())}
 else:d={'city':city,'district':spec['zone'],'origin':origin,'radius':350,'spawn':[0,0],'features':fresh}
 d.update(source='OpenStreetMap contributors',source_url='https://www.openstreetmap.org/copyright',license='ODbL 1.0',retrieved=datetime.date.today().isoformat(),source_sha256=hashlib.sha256(raw).hexdigest())
 output=DATA/(city+'.json.gz');output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
 from backend.api import geography
 for name in ['district','road_segments','footprints','collision_grid','driving_segments','street_grid','safe_spawn']:getattr(geography,name).cache_clear()
 spawn=geography.safe_spawn(city);d['spawn']=list(spawn);output.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
 print(city,'features',len(d['features']),'buildings',sum('building' in f['tags'] for f in d['features']),'spawn',spawn,flush=True)
 return d

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--cities',action='store_true');parser.add_argument('--whitehouse');args=parser.parse_args()
 if args.whitehouse:
  old=json.loads(gzip.decompress((DATA/'milton-keynes.json.gz').read_bytes()));d=save('milton-keynes',Path(args.whitehouse).read_bytes(),old);oldids={str(f['id']) for f in old['features']};added=[f for f in d['features'] if str(f['id']) not in oldids and 'building' in f['tags']];print('New source-supported buildings:',[(f['id'],f['tags'].get('building')) for f in added]);(DATA/'whitehouse-import-audit.json').write_text(json.dumps({'retrieved':d['retrieved'],'source_sha256':d['source_sha256'],'previous_buildings':sum('building' in f['tags'] for f in old['features']),'current_buildings':sum('building' in f['tags'] for f in d['features']),'added_buildings':[{'id':f['id'],'type':f['tags']['building']} for f in added],'scope':'Refresh within existing district; retain older mapped features outside downloaded bounds. No inferred buildings or address publication.'},indent=2))
 if args.cities:
  for c in CITIES:
   if 'origin' not in c:continue
   lat,lon=c['origin']['lat'],c['origin']['lon'];dx=430/(111320*math.cos(math.radians(lat)));dy=430/111320;url=f'https://api.openstreetmap.org/api/0.6/map?bbox={lon-dx},{lat-dy},{lon+dx},{lat+dy}';cache=Path('/tmp')/(c['id']+'-source.osm')
   if not cache.exists():cache.write_bytes(urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MyLilWorlds-Geography-Import/1.0','Accept':'application/xml'}),timeout=45).read())
   save(c['id'],cache.read_bytes())
if __name__=='__main__':main()
