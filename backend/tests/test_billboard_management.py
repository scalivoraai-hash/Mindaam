import math,time,uuid
from sqlalchemy import select,func
from backend.tests.test_core import system,register,onboard
from backend.api.models import User,Audit
from backend.api.operations import AdBoard,AdCampaign,seed_inventory
from backend.api.billboard_placement import prepared_placements,safe
from backend.api.locations import CITIES

def test_all_city_placements_clear_and_separated():
 for city in CITIES:
  points=prepared_placements(city['id']);assert len(points)==3,city['id']
  assert all(safe(city['id'],*p) for p in points)
  assert all(math.dist(a,b)>=60 for i,a in enumerate(points) for b in points[i+1:])

def test_billboard_authority_archive_history_and_seed_idempotence(system):
 c,dbs=system;h,u=register(c);onboard(c,h);x,z=prepared_placements('london')[0]
 body={'city':'london','name':'Reviewed placement','x':x,'z':z,'enabled':True}
 path='/api/super-admin/billboards/london-central-01'
 assert c.put(path,json=body).status_code==401
 assert c.put(path,headers=h,json=body).status_code==403
 with dbs.begin() as db:
  db.get(User,u['id']).role='super_admin';seed_inventory(db)
  db.add(AdCampaign(id='preserved',board_id='london-central-01',advertiser='Existing advertiser',name='Approved campaign',headline='Existing content',starts_at=time.time()-10,ends_at=time.time()+1000,status='active'))
 assert c.put(path,headers=h,json=body).status_code==200
 assert c.put(path,headers=h,json={**body,'x':1e8}).status_code==422
 assert c.delete(path,headers=h).status_code==200
 with dbs.begin() as db:
  seed_inventory(db);assert not db.get(AdBoard,'london-central-01').enabled
  assert db.get(AdCampaign,'preserved').headline=='Existing content'
  assert db.scalar(select(func.count()).select_from(AdBoard).where(AdBoard.city=='london'))==3
 assert all(b['id']!='london-central-01' for b in c.get('/api/ads/boards/london').json())
 assert c.put(path,headers=h,json=body).status_code==200

def test_creatives_decode_and_strip_metadata(system):
 import base64,io
 from PIL import Image
 c,dbs=system;h,u=register(c)
 with dbs.begin() as db:db.get(User,u['id']).role='super_admin'
 image=io.BytesIO();Image.new('RGB',(32,16),'blue').save(image,format='PNG')
 response=c.post('/api/super-admin/creatives',headers=h,json={'content':base64.b64encode(image.getvalue()).decode()})
 assert response.status_code==201,response.text
 fetched=c.get(response.json()['url']);assert fetched.headers['content-type']=='image/jpeg'
 assert Image.open(io.BytesIO(fetched.content)).size==(32,16)
 invalid=b'\x89PNG\r\n\x1a\n'+b'\0'*40
 assert c.post('/api/super-admin/creatives',headers=h,json={'content':base64.b64encode(invalid).decode()}).status_code==422
