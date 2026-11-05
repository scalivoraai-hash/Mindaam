"""Reconcile bounded, public OSM street furniture without changing collision geometry.
Cached XML stays in /tmp; admitted public tags and source provenance are versioned.
"""
import datetime,gzip,hashlib,json,math,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
KEEP={'name','name:en','highway','amenity','railway','barrier','crossing','crossing:signals','direction','traffic_signals:direction','shelter','material','natural'}
def convert(raw,origin):
 result=[]
 for n in ET.fromstring(raw).findall('node'):
  tags={t.attrib['k']:t.attrib['v'] for t in n.findall('tag') if t.attrib['k'] in KEEP}
  if not (tags.get('highway') in {'traffic_signals','street_lamp','bus_stop','crossing'} or tags.get('amenity') in {'bench','waste_basket'} or tags.get('barrier')=='bollard' or tags.get('railway')=='tram_stop'):continue
  lat,lon=float(n.attrib['lat']),float(n.attrib['lon']);id=n.attrib['id']
  result.append({'id':str(2000000000000+int(id)),'osm_type':'node','osm_id':id,'tags':tags,'points':[[round((lon-origin['lon'])*111320*math.cos(math.radians(origin['lat'])),2),round((origin['lat']-lat)*111320,2)]]})
 return result

def main():
 cache=Path('/tmp/mindaam-v2-osm');cache.mkdir(exist_ok=True)
 styles=json.loads((ROOT/'shared/city-visual-styles.json').read_text());audit=[];catalog={}
 for city in styles:
  file=ROOT/'backend/data'/f'{city}.json.gz';d=json.loads(gzip.decompress(file.read_bytes()));origin=d['origin'];lat,lon=origin['lat'],origin['lon'];radius=d['radius']+70;dx=radius/(111320*math.cos(math.radians(lat)));dy=radius/111320;bbox=d.get('extract_bbox',[lon-dx,lat-dy,lon+dx,lat+dy]);url='https://api.openstreetmap.org/api/0.6/map?bbox='+','.join(str(round(n,8)) for n in bbox)
  try:
   rawfile=cache/(city+'.osm')
   if not rawfile.exists():
    raw=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mindaam-OSM-Reconciliation/1.0','Accept':'application/xml'}),timeout=25).read();rawfile.write_bytes(raw)
   raw=rawfile.read_bytes();features=convert(raw,origin);blob=json.dumps({'city':city,'features':features},separators=(',',':'),ensure_ascii=False).encode();digest=hashlib.sha256(blob).hexdigest();asset=ROOT/'apps/consumer-web/public/assets/cities/street-furniture'/f'{city}-{digest[:12]}.json';asset.parent.mkdir(parents=True,exist_ok=True);asset.write_bytes(blob);catalog[city]={'path':'/assets/cities/street-furniture/'+asset.name,'sha256':digest,'nodes':len(features)};row={'city':city,'status':'source reconciled','admitted_nodes':len(features),'signals':sum(f['tags'].get('highway')=='traffic_signals' for f in features),'source':{'url':url,'retrieved':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'license':'ODbL 1.0','scope':'Presentation-only street nodes; authoritative map bytes unchanged'}};print(city,len(features),'nodes',row['signals'],'signals',flush=True)
  except Exception as e:row={'city':city,'status':'unresolved','error':str(e)};print(city,'UNRESOLVED',str(e),flush=True)
  (ROOT/'shared/city-street-furniture.json').write_text(json.dumps(catalog,indent=2));audit.append(row);(ROOT/'docs/evidence/cinematic-v2/street-furniture-import.json').write_text(json.dumps(audit,indent=2))
if __name__=='__main__':main()
