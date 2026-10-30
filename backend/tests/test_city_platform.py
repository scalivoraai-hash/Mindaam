import time,uuid
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,func
from backend.tests.test_core import system,register,onboard
from backend.api.models import User,Presence,Ledger,MediaSession,ConversationMember,Social,Config
from backend.api.transit import Route,Vehicle,Ticket,hub,seed_network
from backend.api.operations import AdBoard,AdCampaign,AdEnquiry,Creative
from backend.api.civic import PublicBuilding
from backend.api.economy import balance

from backend.tests.economy_fixtures import purchased_fixture

def pair(c):
 a=register(c,'city_alice');b=register(c,'city_bob')
 for h,u in [a,b]:onboard(c,h);purchased_fixture(u['id'])
 return a,b

def test_friends_mutual_requests_remove_block_and_cross_world_media(system):
 c,dbs=system;a,b=pair(c)
 assert c.post(f'/api/social/{a[1]["id"]}/friend',headers=a[0]).status_code==404
 path=f'/api/social/{b[1]["id"]}/friend'
 assert c.post(path,headers=a[0]).status_code==200
 assert c.post(path,headers=a[0]).status_code==200
 assert c.get('/api/friends',headers=b[0]).json()[0]['incoming']
 assert c.post(f'/api/social/{a[1]["id"]}/accept',headers=b[0]).status_code==200
 assert all(c.get('/api/friends',headers=h).json()[0]['friend'] for h,u in [a,b])
 assert c.post('/api/growth/worlds/manchester/starter',headers=b[0],json={'confirmed':True}).status_code==200
 assert c.post('/api/world/enter',headers=b[0],json={'city':'manchester'}).status_code==200
 r=c.post('/api/talk/request',headers=a[0],json={'target_id':b[1]['id'],'kind':'voice'});assert r.status_code==200,r.text
 assert r.json()['distance_policy']=='friends'
 assert c.post('/api/messages/'+b[1]['id'],headers=a[0],json={'body':'See you in London'}).status_code==201
 assert c.get('/api/friends',headers=b[0]).json()[0]['unread']==1
 assert c.post(f'/api/social/{b[1]["id"]}/block',headers=a[0]).status_code==200
 assert c.get('/api/friends',headers=b[0]).json()==[]
 assert c.post('/api/messages/'+b[1]['id'],headers=a[0],json={'body':'blocked'}).status_code==403
 assert c.post(path,headers=a[0]).status_code==403

def test_conversation_capacity_authority(system):
 c,dbs=system;a,b=pair(c);outsider=register(c,'city_c')
 for h,u in [a,b]:c.post('/api/world/enter',headers=h,json={'city':'london'})
 r=c.post('/api/talk/request',headers=a[0],json={'target_id':b[1]['id'],'kind':'text'});id=r.json()['id'];assert c.post('/api/talk/'+id+'/accept',headers=b[0]).status_code==200
 assert c.put('/api/talk/conversation/'+id+'/capacity',headers=outsider[0],json={'maximum':4}).status_code==403
 assert c.put('/api/talk/conversation/'+id+'/capacity',headers=a[0],json={'maximum':4}).status_code==200
 assert c.put('/api/talk/conversation/'+id+'/capacity',headers=a[0],json={'maximum':10}).status_code==422
 with dbs.begin() as db:
  assert db.get(MediaSession,id).max_participants==4
  for n in range(2):
   u=User(email=f'cap{n}@example.test',username=f'cap{n}',password_hash='test');db.add(u);db.flush();db.add(ConversationMember(session_id=id,user_id=u.id));db.add(Presence(user_id=u.id,city='london',x=0,z=0))
 assert c.put('/api/talk/conversation/'+id+'/capacity',headers=a[0],json={'maximum':3}).status_code==409

def setup_bus(c,dbs,monkeypatch,capacity=2):
 a,b=pair(c);now=time.time();start=int(now/600)*600
 monkeypatch.setattr('backend.api.transit.time.time',lambda:start+5)
 with dbs.begin() as db:
  db.add(Route(id='test-route',origin='london',destination='manchester',number='101',frequency=600,duration=120,fare=20,capacity=capacity))
  for h,u in [a,b]:
   p=db.get(Presence,u['id'])
   if not p:p=Presence(user_id=u['id'],city='london');db.add(p)
   stop=hub('london');p.x,p.z=stop['x'],stop['z'];p.updated_at=start+5
 for h,u in [a,b]:assert c.post('/api/growth/worlds/manchester/starter',headers=h,json={'confirmed':True}).status_code==200
 return a,b,'test-route:'+str(start),start

def test_bus_atomic_purchase_seats_access_and_safe_exit(system,monkeypatch):
 c,dbs=system;a,b,id,start=setup_bus(c,dbs,monkeypatch)
 for h,u in [a,b]:assert c.post('/api/transit/hail',headers=h,json={'vehicle_id':id}).status_code==200
 ticket={'id':str(uuid.uuid4()),'vehicle_id':id,'expected_currency':'xp','expected_fare':20}
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:c.post('/api/transit/board',headers=a[0],json=ticket),range(2)))
 assert [r.status_code for r in results]==[200,200]
 with dbs() as db:
  assert db.scalar(select(func.count()).select_from(Ledger).where(Ledger.kind=='bus_ticket_xp'))==1
  assert balance(db,a[1]['id'])==50 and balance(db,a[1]['id'],'xp')==0
 assert c.post('/api/transit/board',headers=b[0],json={'id':str(uuid.uuid4()),'vehicle_id':id,'expected_currency':'xp','expected_fare':20}).status_code==200
 with ThreadPoolExecutor(max_workers=2) as pool:seats=list(pool.map(lambda h:c.post('/api/transit/seat',headers=h,json={'seat':1}),[a[0],b[0]]))
 assert sorted(r.status_code for r in seats)==[200,409]
 board=c.get('/api/transit/board/london',headers=a[0]).json();assert board['journey']['passenger_count']==2
 assert c.post('/api/transit/request-stop',headers=a[0]).status_code==200
 monkeypatch.setattr('backend.api.transit.time.time',lambda:start+90)
 assert c.post('/api/transit/exit',headers=a[0]).status_code==409
 monkeypatch.setattr('backend.api.transit.time.time',lambda:start+160)
 assert c.post('/api/transit/exit',headers=a[0]).json()['city']=='manchester'
 with dbs() as db:
  p=db.get(Presence,a[1]['id']);assert p.zone_id=='world';assert balance(db,a[1]['id'])==50 and balance(db,a[1]['id'],'xp')==0
 assert c.post('/api/transit/board',headers=a[0],json=ticket).json()['duplicate']

def test_bus_rejects_full_locked_and_insufficient_without_charge(system,monkeypatch):
 c,dbs=system;a,b,id,start=setup_bus(c,dbs,monkeypatch,1)
 for h,u in [a,b]:c.post('/api/transit/hail',headers=h,json={'vehicle_id':id})
 assert c.post('/api/transit/board',headers=a[0],json={'id':str(uuid.uuid4()),'vehicle_id':id,'expected_currency':'xp','expected_fare':20}).status_code==200
 assert c.post('/api/transit/board',headers=b[0],json={'id':str(uuid.uuid4()),'vehicle_id':id,'expected_currency':'xp','expected_fare':20}).status_code==409
 with dbs.begin() as db:db.get(Vehicle,id).capacity=2;db.get(Vehicle,id).fare=100
 assert c.post('/api/transit/board',headers=b[0],json={'id':str(uuid.uuid4()),'vehicle_id':id,'expected_currency':'xp','expected_fare':100}).json()['detail']['code']=='INSUFFICIENT_XP'
 with dbs() as db:assert balance(db,b[1]['id'])==50
 from backend.api.growth import WorldAccess
 with dbs.begin() as db:
  db.get(Vehicle,id).fare=20;db.delete(db.get(WorldAccess,(b[1]['id'],'manchester')))
 denied=c.post('/api/transit/board',headers=b[0],json={'id':str(uuid.uuid4()),'vehicle_id':id,'expected_currency':'xp','expected_fare':20})
 assert denied.status_code==403 and denied.json()['detail']['code']=='STARTER_CONFIRMATION_REQUIRED'
 with dbs() as db:assert balance(db,b[1]['id'])==50


def test_public_building_isolation_and_private_denial(system):
 c,dbs=system;a,b=pair(c)
 for h,u in [a,b]:c.post('/api/world/enter',headers=h,json={'city':'london'})
 with dbs.begin() as db:db.add(PublicBuilding(id='test-library',city='london',name='Library test fixture',template='library',source_id='test',x=0,z=0))
 assert c.post('/api/buildings/private-home/enter',headers=a[0]).status_code==404
 assert c.post('/api/buildings/test-library/enter',headers=a[0]).status_code==200
 data=c.get('/api/world/london',headers=a[0]).json();assert data['scene']['template']=='library';assert data['players']==[];assert data['collectibles']==[]
 assert c.post('/api/buildings/test-library/enter',headers=b[0]).status_code==200
 with dbs() as db:
  p,q=db.get(Presence,a[1]['id']),db.get(Presence,b[1]['id']);assert (p.x,p.z)!=(q.x,q.z)
 assert c.get('/api/world/london',headers=a[0]).json()['players'][0]['id']==b[1]['id']
 assert c.post('/api/world/move',headers=a[0],json={'dx':1,'dz':0,'mode':'walk'}).status_code==200
 assert c.post('/api/buildings/exit',headers=a[0]).status_code==200
 with dbs.begin() as db:db.get(PublicBuilding,'test-library').enabled=False
 assert c.post('/api/buildings/test-library/enter',headers=a[0]).status_code==404

def test_super_admin_campaign_enquiry_and_schedule(system,monkeypatch):
 c,dbs=system;a,b=pair(c)
 assert c.get('/api/super-admin/overview',headers=a[0]).status_code==403
 with dbs.begin() as db:
  db.get(User,a[1]['id']).role='super_admin';db.add(AdBoard(id='test-board',city='london',name='Test board',x=0,z=0))
 enquiry={'id':str(uuid.uuid4()),'business_name':'Test Brand','contact_name':'Test Contact','email':'contact@example.test','destination_id':'london','board_id':'test-board','consent':True}
 assert c.post('/api/ads/enquiries',headers=b[0],json=enquiry).status_code==201
 assert c.post('/api/ads/enquiries',headers=b[0],json=enquiry).status_code==201
 assert len(c.get('/api/super-admin/enquiries',headers=a[0]).json())==1
 assert c.post('/api/super-admin/creatives',headers=b[0],json={'content':'aGVsbG8='}).status_code==403
 id=str(uuid.uuid4());now=time.time();campaign={'advertiser':'Test Brand','name':'Test campaign','headline':'Test only','board_id':'test-board','starts_at':now-10,'ends_at':now+10,'status':'active'}
 assert c.put('/api/super-admin/campaigns/'+id,headers=a[0],json={**campaign,'cta_url':'javascript:alert(1)'}).status_code==422
 assert c.put('/api/super-admin/campaigns/'+id,headers=a[0],json=campaign).status_code==200
 assert c.get('/api/ads/boards/london').json()[0]['campaign']['headline']=='Test only'
 monkeypatch.setattr('backend.api.operations.time.time',lambda:now+20)
 assert c.get('/api/ads/boards/london').json()[0]['campaign'] is None
 assert c.get('/api/super-admin/overview',headers=a[0]).status_code==200
 with dbs.begin() as db:db.get(User,a[1]['id']).must_change_password=True
 assert c.get('/api/super-admin/overview',headers=a[0]).status_code==403

def test_auditorium_gifts_idempotent_and_chat_setting(system,monkeypatch):
 monkeypatch.setenv("MINDAAM_GRAND_ARENA_ENABLED","true")
 c,dbs=system;a,b=pair(c)
 for h,u in [a,b]:c.post('/api/world/enter',headers=h,json={'city':'london'})
 event=c.post('/api/events',headers=a[0],json={'title':'Test auditorium','city':'london','starts_at':time.time()+60,'capacity':100,'venue_experience_type':'auditorium','venue_mode':'grand_arena','communication_mode':'text'}).json();id=event['id']
 from backend.api.economy import credit
 with dbs.begin() as db:credit(db,a[1]['id'],100,'purchase','fixture','arena-gifts-booking')
 reserved=c.post('/api/events/'+id+'/venue/booking',headers=a[0],json={'request_id':str(uuid.uuid4()),'hours':1,'expected_cost':100,'starts_at':time.time()-1})
 assert reserved.status_code==200,reserved.text
 assert c.post('/api/events/'+id+'/join',headers=b[0]).json()['my_role']=='audience'
 event=c.post('/api/events/'+id+'/state/start',headers=a[0]).json()
 assert c.post('/api/events/'+id+'/venue/enter',headers=b[0]).status_code==200
 snapshot=c.get('/api/world/london',headers=b[0]).json();assert snapshot['scene']['template']=='auditorium'
 assert any(p['id']==a[1]['id'] and p['event_role']=='host' for p in snapshot['players'])
 assert c.post('/api/events/'+id+'/react',headers=b[0],json={'emoji':'👏'}).status_code==200
 body={'id':str(uuid.uuid4()),'gift':'rose','expected_cost':1}
 for _ in range(2):assert c.post('/api/events/'+id+'/gift',headers=b[0],json=body).status_code==200
 with dbs() as db:assert balance(db,b[1]['id'])==49
 with dbs.begin() as db:db.merge(Config(key='event_gifts',value={'rose':2}))
 retry=c.post('/api/events/'+id+'/gift',headers=b[0],json=body)
 assert retry.status_code==200 and retry.json()['cost']==1
 changed=c.post('/api/events/'+id+'/gift',headers=b[0],json={**body,'id':str(uuid.uuid4())})
 assert changed.status_code==409
 with dbs() as db:assert balance(db,b[1]['id'])==49
 assert c.put('/api/events/'+id+'/chat',headers=a[0],json={'enabled':False}).status_code==200
 assert c.post('/api/talk/'+event['session_id']+'/messages',headers=b[0],json={'id':str(uuid.uuid4()),'body':'blocked by host'}).status_code==403
 assert c.post('/api/events/'+id+'/hand',headers=b[0]).json()['raised']
 assert c.post('/api/events/'+id+'/people/'+b[1]['id']+'/decline_hand',headers=a[0]).status_code==200
 assert not c.get('/api/events/'+id,headers=b[0]).json()['my_hand']
 assert c.post('/api/events/'+id+'/people/'+b[1]['id']+'/speaker',headers=a[0]).status_code==200
 with dbs() as db:assert db.get(Presence,b[1]['id']).z==-10

def test_bus_stop_windows_and_travel_bypass_are_rejected(system,monkeypatch):
 c,dbs=system;a,b,id,start=setup_bus(c,dbs,monkeypatch)
 assert c.post('/api/transit/hail',headers=a[0],json={'vehicle_id':id}).status_code==200
 assert c.post('/api/transit/board',headers=a[0],json={'id':str(uuid.uuid4()),'vehicle_id':id,'expected_currency':'xp','expected_fare':20}).status_code==200
 assert c.post('/api/places/travel/visit',headers=a[0],json={'city':'london','place_id':'anything'}).status_code==409
 assert c.post('/api/world/enter',headers=a[0],json={'city':'manchester'}).status_code==409
 from backend.api.transit import position
 with dbs() as db:
  route=db.get(Route,'test-route');v=db.get(Vehicle,id)
  assert position(route,v,start-20)['stopped']
  assert not position(route,v,start-10)['stopped']
  assert position(route,v,start+5)['stopped']
  assert not position(route,v,start+40)['stopped']
  assert position(route,v,start+130)['road_city']=='manchester'
  assert position(route,v,start+151)['stopped']
 monkeypatch.setattr('backend.api.transit.time.time',lambda:start-10)
 assert c.post('/api/transit/exit',headers=a[0]).status_code==409


def test_room_creator_limit_four_rejects_fifth_member(system):
 from backend.tests.test_conversation_groups import group_setup,join
 c,dbs=system;members,id=group_setup(c);a,b,d=members
 assert c.put('/api/talk/conversation/'+id+'/capacity',headers=a[0],json={'maximum':4}).status_code==200
 assert join(c,id,a,d).status_code==200
 fourth=register(c,'city_four');onboard(c,fourth[0]);assert join(c,id,b,fourth).status_code==200
 fifth=register(c,'city_five');onboard(c,fifth[0])
 assert c.post('/api/talk/conversation/'+id+'/join',headers=fifth[0]).status_code==403
 with dbs() as db:assert db.scalar(select(func.count()).select_from(ConversationMember).where(ConversationMember.session_id==id,ConversationMember.state=='active'))==4


def test_public_building_seed_excludes_residences_and_restricted_places(system,monkeypatch):
 from backend.api import civic,locations
 c,dbs=system
 monkeypatch.setattr(locations,'CITIES',[{'id':'london'}])
 features=[{'id':str(i),'tags':tags,'points':[[0,0],[1,0],[1,1],[0,0]]} for i,tags in enumerate([
  {'amenity':'library','name':'Public library'},
  {'amenity':'cafe','name':'Private cafe','access':'private'},
  {'amenity':'library','name':'Home library','building':'house'},
  {'building':'apartments','name':'Apartments'},
  {'amenity':'prison','name':'Restricted prison'},
 ])]
 monkeypatch.setattr(civic,'district',lambda city:{'features':features});monkeypatch.setattr(civic,'entrance',lambda city,p:(0,0))
 with dbs.begin() as db:
  civic.seed_buildings(db);civic.seed_buildings(db)
  rows=list(db.scalars(select(PublicBuilding)));assert len(rows)==1 and rows[0].name=='Public library'


def test_owner_bootstrap_is_one_time_and_requires_password_change(system,monkeypatch):
 from backend.api.operations import bootstrap_owner
 from backend.api.auth import check_password
 c,dbs=system
 monkeypatch.setenv('SUPER_ADMIN_EMAIL','owner@example.test');monkeypatch.setenv('SUPER_ADMIN_USERNAME','test_owner')
 monkeypatch.setenv('SUPER_ADMIN_INITIAL_PASSWORD','local-test-only-long-owner-password')
 with dbs.begin() as db:
  bootstrap_owner(db);bootstrap_owner(db)
  owners=list(db.scalars(select(User).where(User.role=='super_admin')))
  assert len(owners)==1 and owners[0].must_change_password
  assert check_password('local-test-only-long-owner-password',owners[0].password_hash)
 login=c.post('/api/auth/login',json={'email':'test_owner','password':'local-test-only-long-owner-password'})
 assert login.status_code==200
 assert c.get('/api/super-admin/overview',headers={'Authorization':'Bearer '+login.json()['token']}).status_code==403


def test_ticket_fare_quote_and_instance_snapshot(system,monkeypatch):
 c,dbs=system;a,b,id,start=setup_bus(c,dbs,monkeypatch)
 assert c.post('/api/transit/hail',headers=a[0],json={'vehicle_id':id}).status_code==200
 with dbs.begin() as db:db.get(Route,'test-route').fare=5
 assert c.get('/api/transit/board/london',headers=a[0]).json()['routes'][0]['fare']==20
 denied=c.post('/api/transit/board',headers=a[0],json={'id':str(uuid.uuid4()),'vehicle_id':id,'expected_currency':'xp','expected_fare':5})
 assert denied.status_code==409 and denied.json()['detail']['code']=='FARE_CHANGED'
 with dbs() as db:assert balance(db,a[1]['id'])==50
