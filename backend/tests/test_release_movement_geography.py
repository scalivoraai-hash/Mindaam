import math,time
import pytest
from backend.api.locations import CITIES
from backend.api.geography import district,safe_spawn,traversable,safe_step,point_inside
from backend.api.models import Presence
from backend.api.world import OUTDOOR_WALK_SPEED as WALK_SPEED,OUTDOOR_RUN_SPEED as RUN_SPEED,MOVEMENT
from backend.tests.test_core import system,register,onboard

@pytest.mark.parametrize('city',[c['id'] for c in CITIES])
def test_all_districts_have_safe_spawns_and_collision_checked_running(city):
 d=district(city);x,z=safe_spawn(city)
 assert traversable(city,x,z)
 ids=[f['id'] for f in d['features']]
 assert len(ids)==len(set(ids))
 for f in d['features']:
  assert not any(k.startswith('addr:') for k in f['tags'])
  assert all(math.isfinite(v) for p in f['points'] for v in p)
 step=RUN_SPEED*.3
 for dx,dz in [(step,0),(-step,0),(0,step),(0,-step)]:
  nx,nz=safe_step(city,x,z,dx,dz,'run')
  assert traversable(city,nx,nz)
  assert math.hypot(nx-x,nz-z)<=step+.001
 assert not traversable(city,d['radius']+1,0)

def test_run_faster_than_walk_with_server_time_and_diagonal_limits(system):
 c,dbs=system;h,u=register(c,'runner');onboard(c,h)
 distances={}
 for mode in ['walk','run']:
  with dbs.begin() as db:
   p=db.get(Presence,u['id']);p.x=p.z=0;p.last_move=time.time()-5
  r=c.post('/api/world/move',headers=h,json={'dx':1,'dz':1,'mode':mode})
  assert r.status_code==200
  distances[mode]=math.hypot(r.json()['x'],r.json()['z'])
 # Idle starts use one input interval with acceleration, never a banked 300 ms leap.
 dt=MOVEMENT['inputIntervalMs']/1000
 assert distances['run']==pytest.approx(RUN_SPEED/MOVEMENT['accelerationSeconds']*dt*dt)
 assert distances['walk']==pytest.approx(WALK_SPEED/MOVEMENT['accelerationSeconds']*dt*dt)
 assert distances['run']/distances['walk']>1.7
 with dbs.begin() as db:
  p=db.get(Presence,u['id']);p.x=p.z=0;p.motion_speed=RUN_SPEED;p.last_move=time.time()-.3
 r=c.post('/api/world/move',headers=h,json={'dx':1,'dz':.5,'mode':'run'})
 assert math.hypot(r.json()['x'],r.json()['z'])==pytest.approx(RUN_SPEED*.3)
 assert c.post('/api/world/move',headers=h,json={'dx':1,'dz':0,'mode':'car'}).status_code==403

def test_effective_speed_and_stops_depend_on_elapsed_time_not_update_count(system,monkeypatch):
 from backend.api import world
 from backend.api.models import User
 c,sessions=system;h,u=register(c,'elapsed_motion');onboard(c,h)
 clock=[time.time()];monkeypatch.setattr(world.time,'time',lambda:clock[0])
 measured={}
 with sessions.begin() as db:
  user=db.get(User,u['id']);p=db.get(Presence,u['id'])
  for mode,target in [('walk',WALK_SPEED),('run',RUN_SPEED)]:
   for interval in [.06,.12,.24]:
    p.x=p.z=0;p.last_move=clock[0];p.motion_speed=target
    start=clock[0]
    for _ in range(round(2.4/interval)):
     clock[0]+=interval
     world.move(world.Movement(dx=1,dz=0,mode=mode),user,db)
    measured[mode,interval]=p.x/(clock[0]-start)
    assert measured[mode,interval]==pytest.approx(target,rel=1e-5)
    before=p.x;clock[0]+=.12
    stopped=world.move(world.Movement(dx=0,dz=0,mode=mode),user,db)
    assert p.x==before and stopped['speed']==0

def test_existing_rental_calibration_preserves_commercial_snapshot():
 from backend.api.mobility import movement_settings
 old={'speed':18,'acceleration':5,'price':10,'minutes':10,'enabled':True,'name':'Existing bike'}
 value=movement_settings('bike',old)
 assert value['speed']>RUN_SPEED and value['acceleration']>old['acceleration']
 assert {k:v for k,v in value.items() if k not in ['speed','acceleration']}=={k:v for k,v in old.items() if k not in ['speed','acceleration']}
 assert old['speed']==18
