import time,uuid
from datetime import date
from zoneinfo import ZoneInfo
import pytest
from backend.tests.test_core import system,register,onboard
from backend.tests.test_venue_credits_rotation import create
from backend.api.models import User,Ledger
from backend.api.economy import credit,balance
from backend.tests.economy_fixtures import historical_gameplay_fixture,purchased_fixture
from backend.api.venue_time import local_slots
from backend.api import world
from sqlalchemy import select,func

def test_calendar_dst_gap_and_fold():
 spring=list(local_slots(date(2026,3,29),ZoneInfo('Europe/London')))
 autumn=list(local_slots(date(2026,10,25),ZoneInfo('Europe/London')))
 assert len(spring)==46 and len(autumn)==50
 assert len({s['starts_at'] for s in autumn})==50
 assert not any(s['label'].startswith('01:') for s in spring)
 assert len([s for s in autumn if s['label'].startswith('01:30')])==2

@pytest.mark.parametrize('hours',[1,2,10,24])
def test_configured_duration_and_receipt_retry(system,hours):
 c,dbs=system;h,u=register(c);onboard(c,h)
 with dbs.begin() as db:
  db.get(User,u['id']).role='super_admin';credit(db,u['id'],10000,'purchase','test','arena-test')
 assert c.put('/api/super-admin/venue-rentals',headers=h,json={'enabled':True,'prices':{'1':100,'2':200,'10':1000,'24':2400}}).status_code==200
 e=create(c,h,'Grand Arena calendar test');data={'request_id':str(uuid.uuid4()),'hours':hours,'expected_cost':hours*100,'starts_at':time.time()+3600}
 first=c.post('/api/events/'+e['id']+'/venue/booking',headers=h,json=data);assert first.status_code==200,first.text
 retry=c.post('/api/events/'+e['id']+'/venue/booking',headers=h,json=data);assert retry.json()['id']==first.json()['id']
 assert first.json()['ends_at']-first.json()['starts_at']==hours*3600
 with dbs() as db:assert db.scalar(select(func.count()).select_from(Ledger).where(Ledger.kind=='venue_rental'))==1

def test_owner_approved_duration_prices(system):
 c,_=system;h,_=register(c);onboard(c,h);catalog=c.get('/api/venue-rentals/london',headers=h).json()
 assert catalog['durations']==[1,2,10,24]
 assert catalog['prices']['2']==180 and catalog['prices']['10']==700
 assert catalog['prices']['1']==100 and catalog['prices']['24']==1400

def test_ticket_join_refund_and_duplicate_purchase(system):
 c,dbs=system;host,owner=register(c,'organiser');onboard(c,host);guest,user=register(c,'ticketbuyer');onboard(c,guest)
 response=c.post('/api/events',headers=host,json={'title':'Paid public talk','city':'london','starts_at':time.time()+3600,'ticket_price':25})
 assert response.status_code==201,response.text
 id=response.json()['id'];url='/api/events/'+id
 assert c.post(url+'/join',headers=guest).status_code==402
 with dbs.begin() as db:
  original=balance(db,user['id']);credit(db,user['id'],100,'purchase','test','ticket-test')
 data={'request_id':str(uuid.uuid4()),'expected_cost':25};paid=c.post(url+'/tickets',headers=guest,json=data)
 assert paid.status_code==200,paid.text
 assert c.post(url+'/tickets',headers=guest,json=data).json()['id']==paid.json()['id']
 assert c.post(url+'/join',headers=guest).status_code==200
 with dbs() as db:assert balance(db,user['id'])==original+75
 assert c.post(url+'/state/end',headers=host).status_code==409
 assert c.post(url+'/state/cancel',headers=host).status_code==200
 assert c.post(url+'/state/cancel',headers=host).status_code==200
 with dbs() as db:assert balance(db,user['id'])==original+100
 assert c.post(url+'/join',headers=guest).status_code==409

def test_ticket_refund_preserves_only_purchased_eligibility(system):
 from backend.api.venue_rentals import purchased_available
 c,dbs=system;h,u=register(c);onboard(c,h)
 with dbs.begin() as db:
  credit(db,u['id'],20,'purchase','fixture','partial-purchase')
  historical_gameplay_fixture(db,u['id'],100,'earned-fixture')
  assert purchased_available(db,u['id'])==20
  credit(db,u['id'],-50,'event_ticket','test-ticket','test-ticket-debit')
  assert purchased_available(db,u['id'])==0
  credit(db,u['id'],50,'event_ticket_refund','test-ticket','test-ticket-refund')
  assert purchased_available(db,u['id'])==20

def test_arena_requirement_cannot_be_disabled_by_client(system):
 c,_=system;h,_=register(c);onboard(c,h)
 e=create(c,h,'Server enforced reservation')
 assert e['programme']['arena_booking_required'] is True
 assert c.post('/api/events/'+e['id']+'/state/start',headers=h).status_code==409
 payload={'title':e['title'],'city':e['city'],'starts_at':e['starts_at'],'venue_experience_type':'auditorium','programme':{'arena_booking_required':False}}
 changed=c.put('/api/events/'+e['id'],headers=h,json=payload)
 assert changed.status_code==200,changed.text
 assert changed.json()['programme']['arena_booking_required'] is True
 assert c.post('/api/events/'+e['id']+'/state/start',headers=h).status_code==409

def test_strict_prices_and_lighting_bounds():
 from pydantic import ValidationError
 from backend.api.venue_rentals import VenuePrices
 from backend.api.event_presentation import Lighting
 for value in [True,'200',1.5]:
  with pytest.raises(ValidationError):VenuePrices(prices={'1':value,'24':1400})
 for value in [-.001,2.001,float('inf'),float('nan')]:
  with pytest.raises(ValidationError):Lighting(intensity=value)
 assert Lighting(intensity=0).intensity==0
 assert Lighting(intensity=2).intensity==2

def test_every_installed_arena_keeps_collectibles_and_entry_clear():
 import math
 from backend.api.locations import CITIES
 from backend.api.grand_arena import placement
 from backend.api.geography import traversable,inside_building
 from backend.api.world_content import prepared_points
 ids=set()
 for city in CITIES:
  arena=placement(city['id']);assert arena,city['id']
  assert arena['id'] not in ids;ids.add(arena['id'])
  assert all(math.hypot(arena['x']-x,arena['z']-z)>=23 for x,z in prepared_points(city['id'],48)),city['id']
  ex,ez=arena['entrance'];end=[arena['x']+math.sin(arena['heading'])*12,arena['z']+math.cos(arena['heading'])*12]
  for step in range(31):
   x=ex+(end[0]-ex)*step/30;z=ez+(end[1]-ez)*step/30
   assert traversable(city['id'],x,z),city['id']
   assert not inside_building(city['id'],x,z),city['id']

def test_arena_discovery_is_authenticated_and_excludes_unconfirmed_events(system):
 c,_=system;h,_=register(c);onboard(c,h)
 assert c.get('/api/arenas/london').status_code==401
 e=create(c,h,'Unconfirmed arena draft')
 response=c.get('/api/arenas/london',headers=h)
 assert response.status_code==200,response.text
 assert response.json()['id']=='grand-arena:london'
 assert all(row['id']!=e['id'] for row in response.json()['events'])
 assert 'arena' not in c.get('/api/world/london',headers=h).json()

def test_ticket_holder_reminder_and_suspended_host_refund(system):
 from backend.api import events
 from backend.api.models import Event,Notification
 from backend.api.event_tickets import ticket
 c,dbs=system;host,owner=register(c,'reminder_host');guest,user=register(c,'reminder_guest')
 for h in [host,guest]:onboard(c,h)
 purchased_fixture(user['id'],sessions=dbs)
 e=c.post('/api/events',headers=host,json={'title':'Ticket reminder test','city':'london','starts_at':time.time()+250,'ticket_price':10}).json()
 with dbs() as db:before=balance(db,user['id'])
 assert c.post('/api/events/'+e['id']+'/tickets',headers=guest,json={'request_id':str(uuid.uuid4()),'expected_cost':10}).status_code==200
 with dbs.begin() as db:
  db.get(Event,e['id']).reminded=False
  events.maintenance(db);db.flush()
  assert db.scalar(select(Notification.id).where(Notification.user_id==user['id'],Notification.kind=='event.starting',Notification.source==e['id']))
  db.get(User,owner['id']).suspended=True
  events.maintenance(db);db.flush()
  assert db.get(Event,e['id']).status=='cancelled'
  assert ticket(db,e['id'],user['id']).refunded_at is not None
  assert balance(db,user['id'])==before


@pytest.mark.parametrize('hours,cost',[(2,180),(10,700)])
def test_approved_default_price_debit_and_retry(system,hours,cost):
 c,dbs=system;h,u=register(c,'approved_price');onboard(c,h)
 with dbs.begin() as db:credit(db,u['id'],2000,'purchase','test','approved-price-fixture')
 before=c.get('/api/wallet',headers=h).json()['credits']
 e=create(c,h,'Approved duration booking')
 data={'request_id':str(uuid.uuid4()),'hours':hours,'expected_cost':cost,'starts_at':time.time()+3600}
 stale=c.post('/api/events/'+e['id']+'/venue/booking',headers=h,json={**data,'expected_cost':cost+1})
 assert stale.status_code==409
 assert c.get('/api/wallet',headers=h).json()['credits']==before
 first=c.post('/api/events/'+e['id']+'/venue/booking',headers=h,json=data)
 assert first.status_code==200,first.text
 retry=c.post('/api/events/'+e['id']+'/venue/booking',headers=h,json=data)
 assert retry.status_code==200 and retry.json()['id']==first.json()['id']
 assert c.get('/api/wallet',headers=h).json()['credits']==before-cost

@pytest.fixture(autouse=True)
def enable_arena_for_preserved_booking_regressions(monkeypatch):
 monkeypatch.setenv("MINDAAM_GRAND_ARENA_ENABLED","true")
