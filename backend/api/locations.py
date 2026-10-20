"""Enabled districts share one geography, presence and gameplay implementation."""
CITIES=[
 {'id':'milton-keynes-centre','name':'Milton Keynes - City Centre','zone':'City Centre','region':'England'},
 {'id':'milton-keynes-willen','name':'Milton Keynes - Willen Lake','zone':'Willen Lake','region':'England'},
 {'id':'milton-keynes','name':'Milton Keynes - Whitehouse','zone':'Whitehouse','region':'England'},
 {'id':'london','name':'London','zone':'Soho','region':'England'},
 {'id':'birmingham','name':'Birmingham','zone':'Bullring','region':'England'},
 *[{'id':id,'name':name,'zone':'City Centre','region':region,'origin':{'lat':lat,'lon':lon}} for id,name,region,lat,lon in [
 ('manchester','Manchester','England',53.4808,-2.2426),('liverpool','Liverpool','England',53.4084,-2.9916),
 ('leeds','Leeds','England',53.8008,-1.5491),('bristol','Bristol','England',51.4545,-2.5879),
 ('oxford','Oxford','England',51.752,-1.2577),('cambridge','Cambridge','England',52.2053,.1218),
 ('york','York','England',53.959,-1.0815),('brighton','Brighton','England',50.8225,-.1372),
 ('newcastle','Newcastle upon Tyne','England',54.9783,-1.6178),('nottingham','Nottingham','England',52.9548,-1.1581),
 ('cardiff','Cardiff','Wales',51.4816,-3.1791),('edinburgh','Edinburgh','Scotland',55.9533,-3.1883)]]]

# Approved installed maps extend all shared modules. Installation never activates a city.
# A deployment may include a reviewed manifest; the owner must then activate it in Super Admin.
def _installed_manifest():
 import json,re,gzip,logging
 from pathlib import Path
 root=Path(__file__).resolve().parents[1]/'data';path=root/'world-manifest.json'
 if not path.exists():return []
 rows=json.loads(path.read_text());result=[];known={c['id'] for c in CITIES}
 for row in rows:
  id=row.get('id','')
  if id in known or not re.fullmatch('[a-z0-9-]{2,45}',id) or row.get('reviewed') is not True or not row.get('source') or not row.get('license'):continue
  if not re.fullmatch('[A-Z]{2}',row.get('country','')) or not row.get('name') or not (root/(id+'.json.gz')).is_file():continue
  try:
   geo=json.loads(gzip.decompress((root/(id+'.json.gz')).read_bytes()))
   if not geo.get('features') or not geo.get('origin') or len(geo.get('spawn',[]))!=2 or not 50<=geo.get('radius',0)<=10000:continue
  except (ValueError,OSError):continue
  result.append({'id':id,'name':row['name'],'country':row['country'],'region':row.get('region',''),'zone':row.get('zone',row['name']),'origin':geo['origin'],'requires_activation':not row.get('launch_active',False)});known.add(id)
 return result
CITIES.extend(_installed_manifest())
