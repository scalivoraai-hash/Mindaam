import math,time,uuid
import pytest
from sqlalchemy import select
from backend.tests.test_core import system,register,onboard
from backend.tests.test_global_integrations import rental_setup
from backend.api.models import User,Presence,Audit,Config
from backend.api.movement_policy import DEFAULTS,KEY

def owner(c,sessions):
 h,u=register(c,'speedowner')
 with sessions.begin() as db:db.get(User,u['id']).role='super_admin'
 return h

def update(c,h,version=0,**speeds):
 return c.put('/api/super-admin/movement',headers=h,json={'expected_version':version,'reason':'Measured local speed acceptance','speeds':{**DEFAULTS,**speeds}})

def test_permissions_versions_rollback_and_public_privacy(system):
 c,sessions=system;h,u=register(c);a=owner(c,sessions)
 assert c.get('/api/movement/config').json()['speeds']==DEFAULTS
 assert c.get('/api/super-admin/movement').status_code==401
 assert update(c,h).status_code==403
 assert c.post('/api/super-admin/movement/restore',headers=h,json={'expected_version':0,'reason':'Unauthorised restore attempt'}).status_code==403
 r=update(c,a,walk=1.5,run=3);assert r.status_code==200,r.text
 assert r.json()['version']==1
 assert update(c,a).status_code==409
 public=c.get('/api/movement/config').json();assert public['speeds']['walk']==1.5
 assert not {'updated_by','history','defaults'}&public.keys()
 restore=c.post('/api/super-admin/movement/restore',headers=a,json={'expected_version':1,'reason':'Restore approved starting pace'})
 assert restore.status_code==200,restore.text
 assert restore.json()['version']==2 and restore.json()['speeds']==DEFAULTS
 restored=c.post('/api/super-admin/movement/restore',headers=a,json={'expected_version':2,'version':1,'reason':'Restore previously measured pace'})
 assert restored.status_code==200 and restored.json()['speeds']['walk']==1.5
 history=c.get('/api/super-admin/movement',headers=a).json()['history'];assert len(history)==3
 assert history[0]['details']['old']==DEFAULTS and history[0]['details']['new']['walk']==1.5
 with sessions() as db:assert db.get(Config,KEY).value['version']==3

@pytest.mark.parametrize('change',[{'walk':0},{'run':-1},{'walk':3,'run':2},{'car':121},{'scooter':46},{'bike':1000},{'swim':20}])
def test_bounds(system,change):
 c,sessions=system;a=owner(c,sessions);assert update(c,a,**change).status_code==422
 assert c.get('/api/movement/config').json()['version']==0

@pytest.mark.parametrize('city',['milton-keynes','london','new-york','abu-dhabi'])
def test_live_avatar_displacement_uses_saved_speed_and_normalises_diagonals(system,monkeypatch,city):
 from backend.api import world
 c,sessions=system;h,u=register(c);onboard(c,h);a=owner(c,sessions)
 clock=[time.time()];monkeypatch.setattr(world.time,'time',lambda:clock[0])
 for ver,speed in [(0,2),(1,1.25),(2,3)]:
  if ver:assert update(c,a,ver-1,walk=speed,run=5).status_code==200
  with sessions.begin() as db:
   p=db.get(Presence,u['id']);p.city=city;p.zone_id='world';p.x=p.z=0;p.last_move=clock[0];p.motion_speed=20
   user=db.get(User,u['id']);clock[0]+=.12
   r=world.move(world.Movement(dx=1,dz=1,mode='walk'),user,db)
   assert math.hypot(p.x,p.z)==pytest.approx(speed*.12,abs=1e-5)
   assert r['movement_config']['version']==ver
   clock[0]+=.12;before=(p.x,p.z);world.move(world.Movement(dx=0,dz=0),user,db);assert (p.x,p.z)==before

@pytest.mark.parametrize('kind',['bike','ebike','scooter','car'])
def test_existing_rental_live_speed_changes_without_commercial_change(system,monkeypatch,kind):
 from backend.api import mobility
 c,sessions=system;h,u,point=rental_setup(c,sessions,kind);a=owner(c,sessions)
 from backend.api.geography import driving_segments
 segment=next((a,b) for a,b in driving_segments('london') if math.dist(((a[0]+b[0])/2,(a[1]+b[1])/2),point)<.001)
 heading=math.atan2(segment[1][0]-segment[0][0],segment[1][1]-segment[0][1])
 currency='credits' if kind=='scooter' else 'xp';cost=mobility.DEFAULTS[kind]['price']
 r=c.post('/api/mobility/assets/asset_'+kind+'/rent',headers=h,json={'id':str(uuid.uuid4()),'expected_cost':cost,'expected_currency':currency});assert r.status_code==200,r.text
 before=c.get('/api/wallet',headers=h).json();clock=[time.time()];monkeypatch.setattr(mobility.time,'time',lambda:clock[0])
 for version,speed in [(1,10),(2,6)]:
  assert update(c,a,version-1,**{kind:speed}).status_code==200
  with sessions.begin() as db:
   lease=mobility.current(db,db.get(User,u['id']));p=db.get(Presence,u['id']);p.x,p.z=point;lease.heading=heading;lease.speed=120;lease.last_update=clock[0];clock[0]+=.12
   value=mobility.drive(mobility.Drive(throttle=1,steer=0),db.get(User,u['id']),db)
   assert math.dist((p.x,p.z),point)==pytest.approx(speed*.12,abs=1e-5)
   assert value['rental']['settings']['speed']==speed and value['movement_config']['version']==version
   assert lease.settings['price']==cost
 assert c.get('/api/wallet',headers=h).json()==before

@pytest.mark.parametrize('value',['NaN','Infinity',True])
def test_non_numeric_and_non_finite_speeds_rejected(system,value):
 c,sessions=system;a=owner(c,sessions)
 assert update(c,a,walk=value).status_code==422


def test_existing_vehicle_catalogue_uses_same_central_record(system):
 from backend.api.mobility import DEFAULTS as VEHICLES
 c,sessions=system;a=owner(c,sessions)
 assert update(c,a,car=6).status_code==200
 original=c.get('/api/super-admin/vehicles',headers=a).json()['types']['car']
 # A valid commercial edit must not restore the previous hardcoded speed floor.
 r=c.put('/api/super-admin/vehicles/types/car',headers=a,json={**VEHICLES['car'],'speed':6,'price':original['price']})
 assert r.status_code==200,r.text
 assert c.get('/api/movement/config').json()['speeds']['car']==6
 assert c.get('/api/super-admin/vehicles',headers=a).json()['types']['car']['speed']==6


def test_existing_approved_vehicle_maximum_remains_restorable(system):
 c,sessions=system;a=owner(c,sessions)
 with sessions.begin() as db:
  from backend.api.mobility import DEFAULTS as VEHICLES
  db.add(Config(key='rental_types',value={**VEHICLES,'bike':{**VEHICLES['bike'],'speed':110}},updated_at=time.time()))
 initial=c.get('/api/super-admin/movement',headers=a).json()
 assert initial['speeds']['bike']==110 and initial['bounds']['bike'][1]==110
 assert update(c,a,bike=110).status_code==200
 assert update(c,a,1,bike=111).status_code==422
 assert update(c,a,1,bike=80).status_code==200
 restored=c.post('/api/super-admin/movement/restore',headers=a,json={'expected_version':2,'reason':'Restore existing approved maximum'})
 assert restored.status_code==200 and restored.json()['speeds']['bike']==110
