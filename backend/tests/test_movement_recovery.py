import math
import pytest
from backend.api import geography as g

@pytest.mark.parametrize('city',['london','birmingham','milton-keynes'])
def test_route_sweeps_remain_safe(city):
 x,z=g.safe_spawn(city);assert g.traversable(city,x,z)
 travelled=0
 for heading in range(0,360,30):
  for _ in range(12):
   a=math.radians(heading);nx,nz=g.safe_step(city,x,z,math.cos(a)*.6,math.sin(a)*.6)
   assert g.traversable(city,nx,nz)
   assert math.hypot(nx-x,nz-z)<=.60001
   travelled+=math.hypot(nx-x,nz-z);x,z=nx,nz
 assert travelled>10
 assert g.nearest_safe_position(city,x,z)==(x,z)

def test_collision_slides_but_does_not_tunnel(monkeypatch):
 monkeypatch.setattr(g,'traversable',lambda city,x,z,mode='walk':x<1)
 x,z=g.safe_step('test',.9,0,1,1)
 assert x<1 and z>.9
 x,z=g.safe_step('test',0,0,3,0)
 assert x<1

def test_recovery_bounded_and_valid(monkeypatch):
 monkeypatch.setattr(g,'traversable',lambda city,x,z,mode='walk':x>=1)
 point=g.nearest_safe_position('test',0,0,3)
 assert point and math.hypot(*point)<=1.01 and point[0]>=1
 assert g.nearest_safe_position('test',-5,0,3) is None
 assert g.nearest_safe_position('test',2,0,3)==(2,0)

from backend.tests.test_core import system,register,onboard
from backend.api.models import Presence

def test_unstuck_cannot_teleport_valid_users_and_cools_down(system,monkeypatch):
 from backend.api import world
 c,db=system;h,u=register(c,'recoveryqa');onboard(c,h)
 monkeypatch.setattr(world,'APP_ENV','staging')
 assert c.post('/api/growth/worlds/birmingham/starter',headers=h,json={'confirmed':True}).status_code==200
 c.post('/api/world/enter',headers=h,json={'city':'birmingham'})
 before=c.get('/api/world/birmingham',headers=h).json()['position']
 r=c.post('/api/world/unstuck',headers=h,json={})
 assert r.status_code==200,r.text
 assert not r.json()['recovered']
 assert (r.json()['x'],r.json()['z'])==(before['x'],before['z'])
 assert c.post('/api/world/unstuck',headers=h,json={}).status_code==429
 assert c.post('/api/world/unstuck',json={}).status_code==401
