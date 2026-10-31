import time,uuid
import pytest
from backend.tests.test_core import system,register,onboard
from backend.api.models import Event,User,Presence
from backend.api.economy import credit

@pytest.mark.parametrize('mode',['standard','virtual_auditorium'])
@pytest.mark.parametrize('private',[False,True])
@pytest.mark.parametrize('price',[0,25])
def test_independent_venue_visibility_admission(system,mode,private,price):
 c,dbs=system;h,host=register(c,'host');onboard(c,h);g,guest=register(c,'guest');onboard(c,g)
 for auth in [h,g]:assert c.get('/api/world/london',headers=auth).status_code==200
 payload={'title':'Independent venue test','city':'london','starts_at':time.time(),'venue_mode':mode,'visibility':'private' if private else 'public','ticket_price':price,'programme':{'arena_booking_required':True}}
 r=c.post('/api/events',headers=h,json=payload);assert r.status_code==201,r.text
 e=r.json();url='/api/events/'+e['id'];assert not e['arena_booking_required'];assert e['venue_booking'] is None
 assert c.post(url+'/venue/booking',headers=h,json={'request_id':str(uuid.uuid4()),'hours':1,'expected_cost':100}).status_code==409
 assert c.post(url+'/state/start',headers=h).status_code==200
 if private:
  assert c.post(url+'/join',headers=g).status_code==404
  assert c.post(url+'/invite',headers=h,json={'user_id':guest['id']}).status_code==200
  assert c.post(url+'/join',headers=g).json()['my_state']=='pending'
  assert c.post(url+'/people/'+guest['id']+'/approve',headers=h).status_code==200
 if price:
  assert c.post(url+'/join',headers=g).status_code==402
  with dbs.begin() as db:credit(db,guest['id'],100,'purchase','local-fixture','venue-mode-funds')
  data={'request_id':str(uuid.uuid4()),'expected_cost':price}
  first=c.post(url+'/tickets',headers=g,json=data);assert first.status_code==200,first.text
  assert c.post(url+'/tickets',headers=g,json=data).json()['id']==first.json()['id']
  assert c.post(url+'/tickets',headers=h,json=data).status_code==409
 assert c.post(url+'/join',headers=g).status_code==200
 if mode=='virtual_auditorium':
  for auth in [h,g]:
   assert c.post(url+'/venue/enter',headers=auth).status_code==200
   assert c.post(url+'/venue/exit',headers=auth).status_code==200
   assert c.post(url+'/venue/enter',headers=auth).status_code==200
 assert c.get('/api/arenas/london',headers=g).json()['events']==[]

def test_grand_arena_requires_reservation_and_virtual_does_not_block_it(system,monkeypatch):
 monkeypatch.setenv("MINDAAM_GRAND_ARENA_ENABLED","true")
 c,dbs=system;h,u=register(c);onboard(c,h);c.get('/api/world/london',headers=h)
 def create(mode):
  r=c.post('/api/events',headers=h,json={'title':mode+' test','city':'london','starts_at':time.time(),'venue_mode':mode,'programme':{'arena_booking_required':False}});assert r.status_code==201,r.text;return r.json()
 v=create('virtual_auditorium');assert c.post('/api/events/'+v['id']+'/state/start',headers=h).status_code==200
 c.post('/api/events/'+v['id']+'/venue/exit',headers=h)
 e=create('grand_arena');url='/api/events/'+e['id'];assert e['arena_booking_required']
 assert c.post(url+'/state/start',headers=h).status_code==409
 with dbs.begin() as db:credit(db,u['id'],100,'purchase','local-fixture','grand-funds')
 assert c.post(url+'/venue/booking',headers=h,json={'request_id':str(uuid.uuid4()),'hours':1,'expected_cost':100,'starts_at':time.time()}).status_code==200
 assert c.post(url+'/state/start',headers=h).status_code==200
 assert c.get('/api/arenas/london',headers=h).json()['events'][0]['id']==e['id']

def test_legacy_mapping_preserves_record(system):
 from backend.api.venue_modes import mode
 c,dbs=system;h,u=register(c);onboard(c,h)
 with dbs.begin() as db:
  e=Event(host_id=u['id'],city='london',title='Legacy virtual',starts_at=time.time(),venue_experience_type='auditorium',programme={})
  db.add(e);db.flush();assert mode(db,e)=='virtual_auditorium';assert e.venue_mode is None
  e.programme={'arena_booking_required':True};assert mode(db,e)=='grand_arena';assert e.venue_mode is None
