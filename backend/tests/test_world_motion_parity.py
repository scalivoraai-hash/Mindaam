"""Regression coverage for input ordering, content parity and existing ledgers."""
import json,math,time,uuid
from pathlib import Path
import pytest
from sqlalchemy import select,func,delete
from backend.tests.test_core import system,register,onboard
from backend.api.models import Presence,Collectible,Mission,Ledger
from backend.api.geography import traversable,safe_spawn
from backend.api.locations import CITIES
from backend.api.world_content import prepared_points,excluded,seed_world
from backend.api.street_vehicles import placements
from backend.api.mobility import RentalAsset,seed_assets

INTERNATIONAL=[c for c in CITIES if c.get('country','GB')!='GB']

def test_all_installed_worlds_load_valid_trails_without_request_time_generation(monkeypatch):
 from backend.api import world_content
 def unexpected_generation(*args,**kwargs):
  pytest.fail('Installed worlds must ship current trail caches, not generate them during snapshots')
 prepared_points.cache_clear()
 try:
  with monkeypatch.context() as patch:
   patch.setattr(world_content,'trail_points',unexpected_generation)
   for city in CITIES:
    points=prepared_points(city['id'],96)
    assert 12<=len(points)<=96
    assert len(set(map(tuple,points)))==len(points)
    assert all(traversable(city['id'],*p) and not traversable(city['id'],*p,'car') and not excluded(city['id'],*p) for p in points)
 finally:prepared_points.cache_clear()

def receive_motion(ws):
 for _ in range(15):
  d=ws.receive_json()
  if d['type'] in ['motion','motion_error']:return d
 pytest.fail('No movement acknowledgement')

def test_socket_motion_stop_invalid_context_and_duplicate(system):
 c,dbs=system;h,u=register(c,'motion_socket');onboard(c,h)
 with c.websocket_connect('/api/realtime') as ws:
  ws.send_json({'token':h['Authorization'][7:]});state=ws.receive_json()
  assert state['movement_transport']=='input-v1'
  base={'type':'input','seq':1,'city':state['city'],'zone':'world','action':'move','x':1,'z':0,'mode':'run'}
  with dbs.begin() as db:db.get(Presence,u['id']).last_move=time.time()-.2
  ws.send_json(base);a=receive_motion(ws)
  assert a['type']=='motion' and a['position']['x']>state['position']['x']
  ws.send_json({**base,'seq':2,'x':0});b=receive_motion(ws)
  assert b['position']['speed']==0 and b['position']['x']==a['position']['x']
  ws.send_json({**base,'seq':2}) # Duplicate must not move the player.
  ws.send_json({**base,'seq':3,'city':'paris'});err=receive_motion(ws)
  assert err['type']=='motion_error' and 'location changed' in err['message']
  with dbs() as db:assert db.get(Presence,u['id']).x==a['position']['x']
  ws.send_json({**base,'seq':4,'x':99});assert receive_motion(ws)['type']=='motion_error'
  ws.send_json({**base,'seq':5,'x':-1});assert receive_motion(ws)['position']['x']<b['position']['x']


def test_http_rejects_inputs_queued_before_city_or_interior_change(system):
 c,dbs=system;h,u=register(c,'stale_motion');onboard(c,h)
 for context in [{'city':'paris','zone':'world'},{'city':'london','zone':'building:old'}]:
  r=c.post('/api/world/move',headers=h,json={**context,'dx':1,'dz':0,'mode':'walk'})
  assert r.status_code==409

@pytest.mark.parametrize('city',[c['id'] for c in INTERNATIONAL])
def test_all_international_trails_are_safe_distributed_and_both_types(city):
 points=prepared_points(city,48)
 assert len(points)==48 and len(set(map(tuple,points)))==48
 assert all(traversable(city,*p) and not traversable(city,*p,'car') and not excluded(city,*p) for p in points)
 assert max(math.dist(a,b) for a in points for b in points)>50
 assert min(math.dist(a,b) for i,a in enumerate(points) for b in points[i+1:])>=4.99


def test_content_provisioning_preserves_uk_ledger_and_existing_claims(system):
 c,dbs=system;h,u=register(c,'trail_collector');onboard(c,h)
 with dbs.begin() as db:
  uk=[(i.id,i.x,i.z) for i in db.scalars(select(Collectible).where(Collectible.city=='london'))]
  ledger=list(db.scalars(select(Ledger.id)))
  db.execute(delete(Collectible).where(Collectible.city=='paris'));db.execute(delete(Mission).where(Mission.city=='paris'))
  seed_world(db,'paris','Paris');seed_world(db,'paris','Paris');seed_world(db,'london','London')
  rows=list(db.scalars(select(Collectible).where(Collectible.city=='paris')))
  assert len(rows)==48 and {r.kind for r in rows}=={'fruit','gem'}
  assert sum(r.kind=='gem' for r in rows)==12
  assert [(i.id,i.x,i.z) for i in db.scalars(select(Collectible).where(Collectible.city=='london'))]==uk
  assert list(db.scalars(select(Ledger.id)))==ledger
 assert c.post('/api/growth/worlds/paris/starter',headers=h,json={'confirmed':True}).status_code==200
 assert c.post('/api/world/enter',headers=h,json={'city':'paris'}).status_code==200
 item=next(i for i in rows if i.kind=='gem')
 with dbs.begin() as db:p=db.get(Presence,u['id']);p.x=item.x;p.z=item.z
 a=c.post('/api/collectibles/'+item.id+'/claim',headers=h,json={});assert a.status_code==200,a.text
 b=c.post('/api/collectibles/'+item.id+'/claim',headers=h,json={});assert b.status_code==200 and b.json()['already_claimed']
 assert (a.json()['xp'],a.json()['credits'])==(b.json()['xp'],b.json()['credits'])
 with dbs.begin() as db:seed_world(db,'paris','Paris')
 assert c.post('/api/collectibles/'+item.id+'/claim',headers=h,json={}).json()['already_claimed']


def test_street_vehicle_instances_have_stable_classification_and_no_duplicates(system):
 c,dbs=system
 for city in ['milton-keynes','london','paris','dubai','new-york','tokyo']:
  rows=placements(city)
  assert rows and len({a['id'] for a in rows})==len(rows)
  assert {a['classification'] for a in rows}<= {'RENTABLE','SCENERY_ONLY'}
  for a in rows:
   if a['classification']=='RENTABLE':assert traversable(city,a['x'],a['z'],'car' if a['kind']=='car' else 'walk')
  with dbs.begin() as db:
   seed_assets(db);seed_assets(db)
   for a in rows:
    assert bool(db.get(RentalAsset,a['id']))==(a['classification']=='RENTABLE')

@pytest.mark.parametrize('kind',['bike','car'])
def test_street_rental_charge_once_exclusive_and_safe_exit(system,kind):
 from backend.tests.test_global_integrations import login
 from backend.api.mobility import POLICY,RentalLease
 c,dbs=system;h,u=login(c,'street_renter');other,v=login(c,'street_peer')
 a=next(a for a in placements('london') if a['kind']==kind and a['classification']=='RENTABLE')
 with dbs.begin() as db:
  seed_assets(db)
  from backend.api.models import Entitlement
  for user in [u,v]:
   from backend.api.economy import credit
   credit(db,user['id'],100,'test_xp','renter','renter',currency='xp')
   p=db.get(Presence,user['id']);p.x=a['x'];p.z=a['z']
   e=db.get(Entitlement,(user['id'],kind))
   if e:db.delete(e)
 for headers in [h,other]:c.post('/api/mobility/policy',headers=headers,json={'version':POLICY['version'],'accepted':True})
 price=25 if kind=='car' else 10;payload={'id':str(uuid.uuid4()),'expected_currency':'xp','expected_cost':price}
 for _ in range(2):assert c.post('/api/mobility/assets/'+a['id']+'/rent',headers=h,json=payload).status_code==200
 assert c.post('/api/mobility/assets/'+a['id']+'/rent',headers=other,json={'id':str(uuid.uuid4()),'expected_currency':'xp','expected_cost':price}).status_code==409
 assert c.post('/api/world/unstuck',headers=h,json={}).status_code==409
 with dbs() as db:assert db.scalar(select(func.count()).select_from(Ledger).where(Ledger.kind.in_(['car_rental_xp','bike_rental_xp'])))==1
 assert c.post('/api/mobility/exit',headers=h,json={}).status_code==200
 with dbs() as db:
  p=db.get(Presence,u['id']);assert p.mode=='walk' and traversable('london',p.x,p.z)
  assert db.get(RentalAsset,a['id']).active_user_id is None
 assert c.get('/api/wallet',headers=h).json()['credits']==50

@pytest.mark.parametrize('kind',['bike','car'])
def test_acceleration_braking_maximum_and_right_turn(system,monkeypatch,kind):
 from backend.tests.test_global_integrations import rental_setup
 from backend.api import mobility
 from backend.api.models import User
 c,dbs=system;h,u,point=rental_setup(c,dbs,kind)
 price=25 if kind=='car' else 10;id=str(uuid.uuid4())
 assert c.post('/api/mobility/assets/asset_'+kind+'/rent',headers=h,json={'id':id,'expected_currency':'xp','expected_cost':price}).status_code==200
 # Isolate vehicle kinematics; collision sweep is covered on the actual maps.
 monkeypatch.setattr(mobility,'safe_step',lambda city,x,z,dx,dz,mode:(x+dx,z+dz))
 with dbs.begin() as db:
  user=db.get(User,u['id']);lease=db.get(mobility.RentalLease,id);lease.heading=0
  speeds=[]
  for i in range(40):
   lease.last_update=time.time()-.2
   result=mobility.drive(mobility.Drive(throttle=1,steer=0),user,db);speeds.append(result['rental']['speed'])
  assert 0<speeds[0]<speeds[10]<=speeds[-1]
  assert speeds[-1]==mobility.DEFAULTS[kind]['speed']
  assert speeds[-1]>13
  lease.last_update=time.time()-.2;mobility.drive(mobility.Drive(throttle=1,steer=1),user,db)
  assert 0<lease.heading<.5 # Right input turns clockwise in x/z coordinates.
  for _ in range(math.ceil(mobility.DEFAULTS[kind]['speed']/mobility.DEFAULTS[kind]['brake']/.2)+1):
   lease.last_update=time.time()-.2;mobility.drive(mobility.Drive(throttle=-1,steer=0),user,db)
  assert lease.speed==0

def test_diagnostics_require_sustained_stall_and_are_rate_limited(monkeypatch,caplog):
 from backend.api import motion_diagnostics as md
 md._pending.clear();clock=[10.0];monkeypatch.setattr(md.time,'monotonic',lambda:clock[0])
 with caplog.at_level('WARNING',logger='pulseworld.motion'):
  for i in range(40):
   clock[0]+=.1;md.observe('test','paris','world','walk',1,2,True,True)
 assert len(caplog.records)==1
 assert caplog.records[0].motion['event']=='player_stuck'
 md.observe('test','paris','world','walk',1,2,False,False)
 assert 'test' not in md._pending

def test_coalesced_press_release_is_not_collapsed_to_only_stop(monkeypatch):
 import asyncio
 from backend.api import main
 seen=[]
 def motion(token,data):
  seen.append((data.seq,data.x));return {'type':'motion','seq':data.seq}
 monkeypatch.setattr(main,'realtime_state',lambda token:{'type':'state'})
 monkeypatch.setattr(main,'realtime_motion',motion)
 class Socket:
  cookies={};headers={}
  def __init__(self):
   base={'type':'input','city':'paris','zone':'world','action':'move','z':0,'mode':'walk'}
   self.inputs=[json.dumps({**base,'seq':1,'x':1}),json.dumps({**base,'seq':2,'x':0})]
  async def accept(self):pass
  async def receive_json(self):return {'token':'test-only'}
  async def receive_text(self):
   if self.inputs:return self.inputs.pop(0) # Both messages arrive in one network batch.
   await asyncio.Event().wait()
  async def send_json(self,value):
   if value.get('seq')==2:raise main.WebSocketDisconnect()
 asyncio.run(main.realtime(Socket()))
 assert seen==[(1,1),(2,0)]
