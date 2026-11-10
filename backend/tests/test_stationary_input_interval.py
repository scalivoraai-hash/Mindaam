import time
import pytest
from backend.tests.test_core import system,register,onboard
from backend.api import world
from backend.api.models import User,Presence
from backend.api.movement_policy import KEY
from backend.api.models import Config

@pytest.mark.parametrize('idle_seconds',[.02,.2,.3,.49,1])
def test_stationary_press_does_not_integrate_released_time(system,monkeypatch,idle_seconds):
    client,sessions=system
    headers,user=register(client,'stationary_input');onboard(client,headers)
    now=time.time();monkeypatch.setattr(world.time,'time',lambda:now)
    with sessions.begin() as db:
        u=db.get(User,user['id']);p=db.get(Presence,u.id)
        p.x=p.z=0;p.motion_speed=0;p.last_move=now-idle_seconds
        row=db.get(Config,KEY)
        value={'version':1,'speeds':{'walk':10.35,'run':19.6},'updated_at':now}
        if row:row.value=value
        else:db.add(Config(key=KEY,value=value))
        step=world.move_locked(world.Movement(dx=1,dz=0,mode='walk'),u,db,p)
        interval=min(idle_seconds,world.MOVEMENT['inputIntervalMs']/1000)
        expected_speed=10.35*interval/world.MOVEMENT['accelerationSeconds']
        assert step['x']==pytest.approx(expected_speed*interval,abs=1e-6)
        assert step['z']==0
        assert p.motion_speed==pytest.approx(expected_speed,abs=1e-6)

def test_continuous_motion_keeps_elapsed_time_and_release_stops(system,monkeypatch):
    client,sessions=system
    headers,user=register(client,'continuous_input');onboard(client,headers)
    now=time.time();monkeypatch.setattr(world.time,'time',lambda:now)
    with sessions.begin() as db:
        u=db.get(User,user['id']);p=db.get(Presence,u.id)
        p.x=p.z=0;p.motion_speed=2;p.last_move=now-.2
        from backend.api.movement_policy import public
        speed=public(db)['speeds']['walk']
        p.motion_speed=speed
        step=world.move_locked(world.Movement(dx=1,dz=0,mode='walk'),u,db,p)
        assert step['x']==pytest.approx(speed*.2,abs=1e-5)
        stopped=world.move_locked(world.Movement(dx=0,dz=0,mode='walk'),u,db,p)
        assert stopped['x']==step['x'] and stopped['speed']==0 and p.motion_speed==0
