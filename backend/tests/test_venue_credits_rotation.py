import pytest
import time,uuid
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,func
from backend.tests.test_core import system,register,onboard
from backend.api.models import User,Ledger,Collectible,Claim,Presence,Config,Event
from backend.api.economy import credit,balance
from backend.tests.economy_fixtures import historical_gameplay_fixture,purchased_fixture
from backend.api import collectible_rotation as rotation,venue_rentals

def create(c,h,title,start=None):
 r=c.post('/api/events',headers=h,json={'title':title,'city':'london','starts_at':start or time.time()+300,'venue_experience_type':'auditorium','venue_mode':'grand_arena','communication_mode':'liveface','event_type':'Public Talk'})
 assert r.status_code==201,r.text
 return r.json()

def test_purchased_eligibility_overlap_and_atomic_duplicate_reservation(system):
 c,dbs=system;h,u=register(c,'venue_owner');onboard(c,h);other,ou=register(c,'venue_other');onboard(c,other)
 e=create(c,h,'Purchased credit venue test');e2=create(c,other,'Overlapping venue test',e['starts_at'])
 with dbs.begin() as db:historical_gameplay_fixture(db,u['id'],3000,'test-fixture')
 data={'request_id':str(uuid.uuid4()),'hours':3,'expected_cost':250};url=f'/api/events/{e["id"]}/venue/booking'
 assert c.post(url,headers=h,json=data).status_code==409 # earned balance cannot pay a purchased-only fee
 with dbs.begin() as db:
  for user in [u,ou]:credit(db,user['id'],1000,'purchase','local-test-payment','local-test-payment')
 before=c.get('/api/wallet',headers=h).json()['credits']
 with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:c.post(url,headers=h,json=data),range(2)))
 assert [r.status_code for r in responses]==[200,200]
 assert responses[0].json()['id']==responses[1].json()['id']
 with dbs() as db:
  assert db.scalar(select(func.count()).select_from(Ledger).where(Ledger.user_id==u['id'],Ledger.kind=='venue_rental'))==1
  assert balance(db,u['id'])==before-250
 assert c.post(f'/api/events/{e2["id"]}/venue/booking',headers=other,json={**data,'request_id':str(uuid.uuid4())}).status_code==409
 assert c.post(f'/api/events/{e["id"]}/state/start',headers=h).status_code==409 # not before reservation
 with dbs.begin() as db:
  row=venue_rentals.booking(db,e['id']);row.starts_at=time.time()-1;row.ends_at=time.time()+20
 assert c.post(f'/api/events/{e["id"]}/state/start',headers=h).status_code==200
 assert c.post(f'/api/events/{e2["id"]}/state/start',headers=other).status_code==409


def test_admin_catalogues_preserve_merchant_products_and_confirmed_cost(system):
 c,dbs=system;h,u=register(c,'prices_owner');onboard(c,h)
 assert c.get('/api/super-admin/credit-packs',headers=h).status_code==403
 with dbs.begin() as db:db.get(User,u['id']).role='super_admin'
 packs=c.get('/api/super-admin/credit-packs',headers=h).json()['packs']
 new=[{'id':p['id'],'name':p['name'],'credits':p['credits'],'amount_pence':p['amount_pence']} for p in packs]
 new[0]['credits']=210
 assert c.put('/api/super-admin/credit-packs',headers=h,json={'packs':new}).status_code==200
 with dbs() as db:assert 'campaign_1000' in db.get(Config,'commerce_catalog').value
 assert c.get('/api/payments/credits',headers=h).json()['packs'][0]['credits']==210
 assert c.put('/api/super-admin/venue-rentals',headers=h,json={'enabled':True,'prices':{'1':120,'3':260,'6':460,'12':810,'24':1410}}).status_code==200
 e=create(c,h,'Price confirmation test')
 with dbs.begin() as db:credit(db,u['id'],1000,'purchase','local-test-payment','local-test-payment')
 assert c.post(f'/api/events/{e["id"]}/venue/booking',headers=h,json={'request_id':str(uuid.uuid4()),'hours':1,'expected_cost':100}).status_code==409


def test_rotation_is_bounded_lazy_cross_city_and_claim_idempotent(system):
 c,dbs=system;h,u=register(c,'rotating_explorer');onboard(c,h)
 with dbs.begin() as db:
  now=time.time();first=rotation.wave(db,'london',now);second=rotation.wave(db,'london',now+3600)
  assert len(first)==16 and len(second)==16
  assert {o.id for o in first}.isdisjoint(o.id for o in second)
  assert {(o.x,o.z) for o in first}.isdisjoint((o.x,o.z) for o in second)
  assert {'Apple','Gem','Crystal','Treasure'}<=set(o.title for o in first)
  for city in ['birmingham','madrid','dubai','mumbai','new-york','sydney']:assert len(rotation.wave(db,city,now))==16
  item=first[0];p=db.get(Presence,u['id']);p.x=item.x;p.z=item.z;p.updated_at=now
  assert db.get(Collectible,item.id) is None
  before=db.scalar(select(func.count()).select_from(Collectible))
 snapshot=c.get('/api/world/london',headers=h).json()
 assert any(i['id']==item.id for i in snapshot['collectibles'])
 with dbs() as db:assert db.scalar(select(func.count()).select_from(Collectible))==before
 with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:c.post('/api/collectibles/'+item.id+'/claim',headers=h),range(2)))
 assert [r.status_code for r in responses]==[200,200]
 assert sum(r.json()['awarded_xp'] for r in responses)==(5 if item.kind=='fruit' else 15)
 assert not any(i['id']==item.id for i in c.get('/api/world/london',headers=h).json()['collectibles'])
 with dbs() as db:assert db.scalar(select(func.count()).select_from(Claim).where(Claim.collectible_id==item.id))==1
 # An impossible remote item cannot even materialise a database instance.
 far=max(first,key=lambda q:(q.x-item.x)**2+(q.z-item.z)**2)
 assert c.post('/api/collectibles/'+far.id+'/claim',headers=h).status_code==409
 with dbs() as db:assert db.get(Collectible,far.id) is None


def test_rotation_rate_limit_is_server_side_and_authored_items_preserved(system):
 c,dbs=system;h,u=register(c,'limited_explorer');onboard(c,h)
 with dbs.begin() as db:
  items=rotation.wave(db,'london');p=db.get(Presence,u['id']);p.x=items[0].x;p.z=items[0].z;p.updated_at=time.time()
  db.add(Config(key='collectible_rotation',value={**rotation.DEFAULTS,'minimum_claim_seconds':5}))
  db.add(Collectible(id='authored-test-trail',city='london',title='Authored trail',kind='gem',x=items[1].x,z=items[1].z))
 assert c.post('/api/collectibles/'+items[0].id+'/claim',headers=h).status_code==200
 with dbs.begin() as db:p=db.get(Presence,u['id']);p.x=items[1].x;p.z=items[1].z;p.updated_at=time.time()
 assert c.post('/api/collectibles/'+items[1].id+'/claim',headers=h).status_code==429
 with dbs.begin() as db:db.get(Config,'collectible_rotation').value={**rotation.DEFAULTS,'enabled':False}
 view=c.get('/api/world/london',headers=h).json()
 assert view['collectibles'] and not any(v['id']==items[1].id for v in view['collectibles'])

@pytest.fixture(autouse=True)
def enable_arena_for_preserved_booking_regressions(monkeypatch):
 monkeypatch.setenv("MINDAAM_GRAND_ARENA_ENABLED","true")
