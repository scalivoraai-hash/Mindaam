import time,uuid
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,func
from backend.tests.test_core import system,register,onboard
from backend.api.models import User,Audit,Presence,Ledger,Config
from backend.api.expansion import Destination,INTERNATIONAL,DemandShareAction
from backend.api.discovery import CityInterest
from backend.api.growth import WorldAccess

def owner(dbs,id):
 with dbs.begin() as db:db.get(User,id).role='super_admin'

def test_curated_catalogue_flags_and_active_world_access(system):
 c,dbs=system;h,u=register(c);onboard(c,h)
 rows=c.get('/api/cities').json();by={d['id']:d for d in rows}
 assert all(by[id]['country']==country and by[id]['flag'] and by[id]['enabled'] for id,name,country,region in INTERNATIONAL)
 assert by['shanghai']['status']=='ACTIVE'
 assert len([d for d in rows if d['enabled']])==45
 assert all(by[id]['name'].startswith('Milton Keynes - ') for id in ['milton-keynes','milton-keynes-centre','milton-keynes-willen'])
 assert all(d['online']==0 for d in rows if not d['enabled'])
 assert c.post('/api/world/enter',headers=h,json={'city':'tokyo'}).status_code==403
 assert c.post('/api/growth/worlds/tokyo/starter',headers=h,json={'confirmed':True}).status_code==200
 assert c.post('/api/world/enter',headers=h,json={'city':'tokyo'}).status_code==200
 assert c.get('/api/growth/worlds',headers=h).json()['starter_selected']==2

def test_demand_unique_threshold_approval_and_private_visibility(system):
 c,dbs=system;a,ua=register(c,'demand_a');b,ub=register(c,'demand_b');owner(dbs,ua['id'])
 assert c.put('/api/super-admin/demand/settings',headers=b,json={'threshold':2}).status_code==403
 assert c.put('/api/super-admin/demand/settings',headers=a,json={'threshold':2}).status_code==200
 with ThreadPoolExecutor(max_workers=4) as pool:replies=list(pool.map(lambda _:c.post('/api/destinations/beijing/interest',headers=b,json={}),range(4)))
 assert all(r.status_code==200 for r in replies)
 assert all(r.json()['interested_count']==1 for r in replies)
 result=c.post('/api/destinations/beijing/interest',headers=a,json={}).json()
 assert result['status']=='QUALIFIED' and result['interested_count']==2
 with dbs() as db:
  assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action=='destination.qualified',Audit.target=='beijing'))==1
  assert not db.get(WorldAccess,(ub['id'],'beijing'))
 body={'name':'Beijing','country':'CN','region':'Asia','status':'ACTIVE','threshold':2}
 assert c.put('/api/super-admin/destinations/beijing',headers=a,json=body).json()['detail']['code']=='WORLD_DATA_REQUIRED'
 assert c.put('/api/super-admin/destinations/beijing',headers=a,json={**body,'status':'IN_PREPARATION'}).status_code==200
 assert c.put('/api/super-admin/destinations/beijing',headers=a,json={**body,'status':'DISABLED'}).status_code==200
 assert 'beijing' not in {d['id'] for d in c.get('/api/cities?include_disabled=true').json()}
 assert 'beijing' in {d['id'] for d in c.get('/api/super-admin/demand',headers=a).json()['destinations']}

def test_demand_shares_do_not_vote_or_unlock_and_links_are_private(system):
 c,dbs=system;a,ua=register(c,'share_a');b,ub=register(c,'share_b');onboard(c,a);onboard(c,b)
 inv=c.post('/api/destinations/chicago/share-link',headers=a).json();code=inv['code']
 assert ua['id'] not in code and len(code)>=20
 assert c.post('/api/destinations/chicago/share-link',headers=a).json()['code']==code
 page=c.get('/api/destination-requests/'+code).json();assert set(page)=={'destination','code'}
 body={'id':str(uuid.uuid4()),'channel':'whatsapp'}
 for _ in range(2):assert c.post(f'/api/destination-requests/{code}/shared',headers=a,json=body).status_code==202
 assert c.post(f'/api/destination-requests/{code}/opened').status_code==202
 assert c.get('/api/destination-requests/'+code).json()['destination']['interested_count']==0
 vote=c.post('/api/destinations/chicago/interest',headers=b,json={'source':'shared-request','invite_code':code});assert vote.status_code==200 and vote.json()['interested_count']==1
 with dbs() as db:
  assert db.scalar(select(func.count()).select_from(DemandShareAction))==1
  assert db.get(CityInterest,(ub['id'],'chicago')).invite_code==code
  assert not db.get(WorldAccess,(ua['id'],'chicago'))
 assert c.post(f'/api/destination-requests/{code}/shared',headers=b,json={'id':str(uuid.uuid4()),'channel':'copy'}).status_code==403
