import time,uuid
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,func
from backend.tests.test_core import system,register,onboard
from backend.api.models import User,Presence,Ledger,Entitlement,Config,MediaSession,ConversationMember
from backend.api.civic import PublicBuilding,InteriorVisit
from backend.api.mobility import RentalAsset,RentalLease,RentalConsent,POLICY,DEFAULTS
from backend.api.gifts import GiftDelivery
from backend.api.geography import safe_spawn,traversable,driving_segments

from backend.tests.economy_fixtures import purchased_fixture

def login(c,name):
 h,u=register(c,name);onboard(c,h);purchased_fixture(u['id']);return h,u

def test_exit_survives_presence_timeout_and_closed_building(system):
 c,dbs=system;h,u=login(c,'exit_recovery');x,z=safe_spawn('london')
 with dbs.begin() as db:
  db.add(PublicBuilding(id='safe-library',city='london',name='Test library',template='library',source_id='test',x=x,z=z));p=db.get(Presence,u['id']);p.x,p.z=x,z
 assert c.post('/api/buildings/safe-library/enter',headers=h).status_code==200
 with dbs.begin() as db:db.delete(db.get(Presence,u['id']))
 restored=c.post('/api/world/enter',headers=h,json={'city':'london'});assert restored.status_code==200 and restored.json()['scene']['id']=='safe-library'
 with dbs.begin() as db:db.delete(db.get(Presence,u['id']));db.get(PublicBuilding,'safe-library').enabled=False
 r=c.post('/api/buildings/exit',headers=h);assert r.status_code==200 and r.json()['position']['zone_id']=='world'
 assert traversable('london',r.json()['position']['x'],r.json()['position']['z'])
 assert c.post('/api/buildings/exit',headers=h).status_code==200
 with dbs() as db:assert db.get(InteriorVisit,u['id']) is None

def test_world_selection_recovers_saved_interior_in_other_city(system):
 c,dbs=system;h,u=login(c,'cross_city_exit');x,z=safe_spawn('london')
 with dbs.begin() as db:
  db.add(PublicBuilding(id='saved-cafe',city='london',name='Saved cafe',template='cafe',source_id='test',x=x,z=z));p=db.get(Presence,u['id']);p.x,p.z=x,z
 assert c.post('/api/buildings/saved-cafe/enter',headers=h).status_code==200
 with dbs.begin() as db:db.delete(db.get(Presence,u['id']))
 # An inaccessible world must not bypass access or consume the saved visit.
 assert c.post('/api/world/enter',headers=h,json={'city':'leeds'}).status_code==403
 with dbs() as db:assert db.get(InteriorVisit,u['id']) is not None
 assert c.post('/api/growth/worlds/leeds/starter',headers=h,json={'confirmed':True}).status_code==200
 recovered=c.post('/api/world/enter',headers=h,json={'city':'leeds'})
 assert recovered.status_code==200 and recovered.json()['position']['zone_id']=='world' and recovered.json()['city']=='leeds'
 with dbs() as db:assert db.get(InteriorVisit,u['id']) is None
 assert c.get('/api/wallet',headers=h).json()['credits']==50

def test_physical_exit_and_no_paywall(system):
 c,dbs=system;h,u=login(c,'door_exit');x,z=safe_spawn('london')
 with dbs.begin() as db:
  db.add(PublicBuilding(id='door',city='london',name='Door test',template='cafe',source_id='test',x=x,z=z));p=db.get(Presence,u['id']);p.x,p.z=x,z
 c.post('/api/buildings/door/enter',headers=h)
 with dbs.begin() as db:p=db.get(Presence,u['id']);p.x,p.z=0,13.3;p.last_move=time.time()-1
 result=c.post('/api/world/move',headers=h,json={'dx':0,'dz':1,'mode':'walk'});assert result.status_code==200 and result.json()['exited']
 assert c.get('/api/wallet',headers=h).json()['credits']==50

def rental_setup(c,dbs,kind='car'):
 h,u=login(c,'renter_'+kind)
 point=next(((a[0]+b[0])/2,(a[1]+b[1])/2) for a,b in driving_segments('london') if traversable('london',(a[0]+b[0])/2,(a[1]+b[1])/2,'car'))
 with dbs.begin() as db:
  from backend.api.economy import credit
  credit(db,u['id'],100,'test_xp','renter','renter',currency='xp')
  db.add(RentalAsset(id='asset_'+kind,city='london',kind=kind,x=point[0],z=point[1]));p=db.get(Presence,u['id']);p.x,p.z=point
  e=db.get(Entitlement,(u['id'],kind))
  if e:db.delete(e)
 assert c.post('/api/mobility/policy',headers=h,json={'version':POLICY['version'],'accepted':True}).status_code==200
 return h,u,point

def test_rental_exclusive_idempotent_debit_acceleration_exit(system):
 c,dbs=system;h,u,point=rental_setup(c,dbs);other,v=login(c,'other_renter')
 with dbs.begin() as db:p=db.get(Presence,v['id']);p.x,p.z=point
 c.post('/api/mobility/policy',headers=other,json={'version':POLICY['version'],'accepted':True})
 body={'id':str(uuid.uuid4()),'expected_currency':'xp','expected_cost':25}
 with ThreadPoolExecutor(max_workers=2) as pool:replies=list(pool.map(lambda _:c.post('/api/mobility/assets/asset_car/rent',headers=h,json=body),range(2)))
 assert all(r.status_code==200 for r in replies),[r.text for r in replies]
 assert c.post('/api/mobility/assets/asset_car/rent',headers=other,json={'id':str(uuid.uuid4()),'expected_currency':'xp','expected_cost':25}).status_code==409
 with dbs() as db:
  assert db.scalar(select(func.count()).select_from(Ledger).where(Ledger.kind.in_(['car_rental_xp','bike_rental_xp'])))==1
  assert db.get(RentalLease,body['id']).price==25
 assert c.post('/api/world/move',headers=h,json={'dx':1,'dz':0,'mode':'run'}).status_code==409
 with dbs.begin() as db:db.get(RentalLease,body['id']).last_update=time.time()-.25
 first=c.post('/api/mobility/drive',headers=h,json={'throttle':1,'steer':0});assert first.status_code==200,first.text
 assert 0<=first.json()['rental']['speed']<DEFAULTS['car']['speed']
 assert c.post('/api/buildings/exit',headers=h).status_code==200 # Unrelated exit cannot terminate lease or charge.
 assert c.post('/api/mobility/exit',headers=h).status_code==200
 with dbs() as db:
  p=db.get(Presence,u['id']);assert p.mode=='walk' and traversable(p.city,p.x,p.z)
  assert db.get(RentalAsset,'asset_car').active_user_id is None
 assert c.post('/api/mobility/exit',headers=h).status_code==200
 assert c.get('/api/wallet',headers=h).json()['credits']==50

def test_rental_policy_price_and_stale_presence_recovery(system):
 c,dbs=system;h,u,point=rental_setup(c,dbs,'bike')
 with dbs.begin() as db:db.delete(db.get(RentalConsent,(u['id'],POLICY['version'])))
 body={'id':str(uuid.uuid4()),'expected_currency':'xp','expected_cost':10}
 assert c.post('/api/mobility/assets/asset_bike/rent',headers=h,json=body).status_code==409
 c.post('/api/mobility/policy',headers=h,json={'version':POLICY['version'],'accepted':True})
 assert c.post('/api/mobility/assets/asset_bike/rent',headers=h,json={**body,'expected_currency':'xp','expected_cost':1}).status_code==409
 assert c.post('/api/mobility/assets/asset_bike/rent',headers=h,json=body).status_code==200
 with dbs.begin() as db:db.delete(db.get(Presence,u['id']))
 r=c.post('/api/world/enter',headers=h,json={'city':'london'});assert r.status_code==200 and r.json()['rental'] is None
 assert c.get('/api/wallet',headers=h).json()['credits']==50

def test_gift_context_recipient_wallet_and_history(system):
 c,dbs=system;a,ua=login(c,'gift_sender');b,ub=login(c,'gift_receiver');outsider,uc=login(c,'gift_outside')
 sid=c.post('/api/talk/request',headers=a,json={'target_id':ub['id'],'kind':'text'}).json()['id'];assert c.post('/api/talk/'+sid+'/accept',headers=b).status_code==200
 body={'id':str(uuid.uuid4()),'context_type':'conversation','context_id':sid,'gift_id':'rose','recipient_id':ub['id'],'expected_cost':1}
 assert c.post('/api/gifts/send',headers=outsider,json=body).status_code==403
 assert c.post('/api/gifts/send',headers=a,json={**body,'recipient_id':uc['id']}).status_code==403
 with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(lambda _:c.post('/api/gifts/send',headers=a,json=body),range(3)))
 assert all(r.status_code==200 for r in results),[r.text for r in results]
 assert c.get('/api/wallet',headers=a).json()['credits']==49 and c.get('/api/wallet',headers=b).json()['credits']==50
 activity=c.get('/api/social-activity/conversation/'+sid,headers=b).json();assert len(activity['gifts'])==1 and activity['gifts'][0]['recipient']==ub['username']
 with dbs.begin() as db:
  assert db.scalar(select(func.count()).select_from(GiftDelivery))==1
  db.get(User,ua['id']).role='super_admin'
 assert c.put('/api/super-admin/gifts/rose',headers=a,json={'name':'Rose','icon':'🌹','price':8}).status_code==200
 assert c.post('/api/gifts/send',headers=a,json=body).json()['gift']['price']==1
 assert c.post('/api/gifts/send',headers=a,json={**body,'id':str(uuid.uuid4())}).status_code==409
 assert c.post('/api/social/'+ub['id']+'/block',headers=a).status_code==200
 assert c.post('/api/gifts/send',headers=a,json={**body,'id':str(uuid.uuid4()),'expected_cost':8}).status_code in [403,409]

def test_free_reactions_idempotency_rate_limit(system):
 c,dbs=system;a,ua=login(c,'react_sender');b,ub=login(c,'react_receiver');sid=c.post('/api/talk/request',headers=a,json={'target_id':ub['id'],'kind':'text'}).json()['id'];c.post('/api/talk/'+sid+'/accept',headers=b)
 body={'id':str(uuid.uuid4()),'context_type':'conversation','context_id':sid,'emoji':'👏'}
 for _ in range(2):assert c.post('/api/reactions',headers=a,json=body).status_code==200
 for _ in range(3):assert c.post('/api/reactions',headers=a,json={**body,'id':str(uuid.uuid4())}).status_code==200
 assert c.post('/api/reactions',headers=a,json={**body,'id':str(uuid.uuid4())}).status_code==429
 assert c.get('/api/wallet',headers=a).json()['credits']==50

def test_water_zones_boundary_multiplayer_and_safe_exit(system):
 c,dbs=system;h,u=login(c,'swimmer');b,ub=login(c,'swimmer_two')
 from backend.api.mobility import WaterZone,seed_water
 from backend.api.geography import point_inside
 with dbs.begin() as db:seed_water(db)
 for head,person in [(h,u),(b,ub)]:
  assert c.post('/api/growth/worlds/milton-keynes-willen/starter',headers=head,json={'confirmed':True}).status_code==200
  assert c.post('/api/world/enter',headers=head,json={'city':'milton-keynes-willen'}).status_code==200
  with dbs.begin() as db:
   z=db.get(WaterZone,'willen-virtual-recreation');assert z and z.enabled
   p=db.get(Presence,person['id']);p.x,p.z=z.shore_x,z.shore_z
  c.post('/api/mobility/policy',headers=head,json={'version':POLICY['version'],'accepted':True})
  r=c.post('/api/mobility/assets/willen-virtual-recreation:swim/rent',headers=head,json={'id':str(uuid.uuid4()),'expected_cost':0});assert r.status_code==200,r.text
 with dbs.begin() as db:
  lease=db.scalar(select(RentalLease).where(RentalLease.user_id==u['id'],RentalLease.ended_at==None));lease.last_update=time.time()-1;lease.speed=3
 r=c.post('/api/mobility/drive',headers=h,json={'throttle':1,'steer':1});assert r.status_code==200
 with dbs() as db:
  z=db.get(WaterZone,'willen-virtual-recreation');p=db.get(Presence,u['id']);assert point_inside(p.x,p.z,z.boundary)
 assert c.post('/api/mobility/exit',headers=h).status_code==200
 with dbs() as db:p=db.get(Presence,u['id']);assert traversable(p.city,p.x,p.z) and not point_inside(p.x,p.z,z.boundary)
 assert c.post('/api/mobility/assets/willen-virtual-recreation:boat/rent',headers=h,json={'id':str(uuid.uuid4()),'expected_cost':20}).status_code==200
 assert c.post('/api/mobility/exit',headers=h).status_code==200
 assert c.get('/api/wallet',headers=h).json()['credits']==30

def test_mall_parent_cards_templates_tenant_security(system,monkeypatch):
 c,dbs=system;h,u=login(c,'mall_visitor');other,v=login(c,'merchant_manager')
 from backend.api import locations
 from backend.api.business_spatial import seed_businesses,BusinessSpatial,BusinessMember
 from backend.api.commerce import Business
 monkeypatch.setattr(locations,'CITIES',[x for x in locations.CITIES if x['id']=='milton-keynes-centre'])
 with dbs.begin() as db:
  seed_businesses(db)
  store=db.scalar(select(BusinessSpatial).where(BusinessSpatial.parent_building_id!=None));store_id=store.business_id;parent=store.parent_building_id
  mall=db.get(PublicBuilding,parent);mx,mz=mall.x,mall.z
  count=db.scalar(select(func.count()).select_from(BusinessSpatial));seed_businesses(db);assert db.scalar(select(func.count()).select_from(BusinessSpatial))==count
 assert c.get('/api/business-cards/'+store_id,headers=h).json()['parent_building_id']==parent
 assert c.get('/api/business-cards/'+store_id,headers=h).json()['assistant_enabled'] is False
 assert c.get('/api/businesses/'+store_id+'/spatial-analytics',headers=h).status_code==404
 with dbs.begin() as db:db.get(Business,store_id).owner_id=u['id'];db.add(BusinessMember(business_id=store_id,user_id=v['id']))
 assert c.get('/api/businesses/'+store_id+'/spatial-analytics',headers=other).status_code==200
 assert c.put('/api/businesses/'+store_id+'/profile',headers=other,json={'website':'javascript:alert(1)'}).status_code==422
 assert c.post('/api/growth/worlds/milton-keynes-centre/starter',headers=h,json={'confirmed':True}).status_code==200
 assert c.post('/api/world/enter',headers=h,json={'city':'milton-keynes-centre'}).status_code==200
 assert c.post('/api/business-cards/'+store_id+'/enter',headers=h).status_code==409
 with dbs.begin() as db:p=db.get(Presence,u['id']);p.x,p.z=mx,mz
 assert c.post('/api/buildings/'+parent+'/enter',headers=h).status_code==200
 listing=c.get('/api/buildings/'+parent+'/directory',headers=h);assert listing.status_code==200 and len(listing.json()['shops'])>24
 doors=[(r['door']['x'],r['door']['z']) for r in listing.json()['shops']];assert len(set(doors))==len(doors)
 mall_scene=c.get('/api/world/milton-keynes-centre',headers=h).json()['scene'];assert len(mall_scene['shops'])==len(doors) and mall_scene['back']<min(z for x,z in doors)
 with dbs.begin() as db:p=db.get(Presence,u['id']);p.x,p.z=0,min(z for x,z in doors);p.last_move=time.time()-1
 moved=c.post('/api/world/move',headers=h,json={'dx':0,'dz':-1,'mode':'walk'});assert moved.status_code==200 and moved.json()['z']<-15
 assert c.post('/api/business-cards/'+store_id+'/enter',headers=h).status_code==200
 scene=c.get('/api/world/milton-keynes-centre',headers=h).json()['scene'];assert scene['id']=='store:'+store_id and scene['template']!='mall' and scene['parent_building_id']==parent
 assert c.post('/api/business-cards/'+store_id+'/back-to-mall',headers=h).status_code==200
 assert c.post('/api/buildings/exit',headers=h).status_code==200

def test_gifts_shared_conversation_media_and_event_audience(system):
 c,dbs=system;a,ua=login(c,'all_gift_a');b,ub=login(c,'all_gift_b');d,ud=login(c,'all_gift_c')
 root=c.post('/api/talk/request',headers=a,json={'target_id':ub['id'],'kind':'text'}).json()['id'];c.post('/api/talk/'+root+'/accept',headers=b)
 with dbs.begin() as db:
  db.add(ConversationMember(session_id=root,user_id=ud['id'],state='active'))
  for mode in ['voice','liveface']:
   room=MediaSession(id='gift-'+mode,requester=ua['id'],target=ub['id'],kind=mode,state='accepted',accepted_at=time.time(),conversation_id=root);db.add(room);db.flush()
   for user in [ua,ub,ud]:db.add(ConversationMember(session_id=room.id,user_id=user['id'],state='active'))
 for sid in [root,'gift-voice','gift-liveface']:
  body={'id':str(uuid.uuid4()),'context_type':'conversation','context_id':sid,'recipient_id':ud['id'],'gift_id':'coffee','expected_cost':3}
  r=c.post('/api/gifts/send',headers=a,json=body);assert r.status_code==200,r.text
 assert len(c.get('/api/social-activity/conversation/'+root,headers=d).json()['gifts'])==3
 from backend.api.models import Event,Attendee
 with dbs.begin() as db:
  e=Event(id='gift-auditorium',host_id=ua['id'],city='london',title='Local test show',description='Automated test only',starts_at=time.time()-1,ends_at=time.time()+3600,status='live',visibility='public',venue_experience_type='auditorium');db.add(e);db.flush()
  for person in [ua,ub,ud]:db.add(Attendee(event_id=e.id,user_id=person['id'],state='active',role='host' if person==ua else 'audience'))
 r=c.post('/api/gifts/send',headers=b,json={'id':str(uuid.uuid4()),'context_type':'event','context_id':'gift-auditorium','recipient_id':ua['id'],'gift_id':'rose','expected_cost':1});assert r.status_code==200,r.text
 assert c.get('/api/social-activity/event/gift-auditorium',headers=d).json()['gifts'][0]['recipient']==ua['username']

def test_transit_speed_preserved_with_outdoor_hierarchy():
 from backend.api.transit import bus_fraction
 length=1000;start=1000
 speed=(bus_fraction(start+32.1,start,length)-bus_fraction(start+32,start,length))*length/.1
 from backend.api.world import OUTDOOR_RUN_SPEED as RUN_SPEED,OUTDOOR_WALK_SPEED as WALK_SPEED
 assert 45.9<speed<46.1 and DEFAULTS['car']['speed']>DEFAULTS['bike']['speed']>RUN_SPEED>WALK_SPEED
