"""Expanded admin limits keep the original integration and swept collision rules."""
import time, math
from types import SimpleNamespace
import pytest
from backend.tests.test_core import system, register, onboard
from backend.tests.test_movement_policy import owner, update
from backend.api.models import User, Presence
from backend.api import world
from backend.api.movement_policy import DEFAULTS

def test_full_caps_are_configurable_defaults_unchanged(system):
    c, sessions = system
    headers = owner(c, sessions)
    initial = c.get('/api/super-admin/movement', headers=headers).json()
    assert initial['speeds'] == DEFAULTS
    assert initial['bounds']['walk'][1] == initial['bounds']['run'][1] == 100
    assert update(c, headers, walk=100, run=100).status_code == 200
    assert update(c, headers, 1, run=100.01).status_code == 422
    assert c.get('/api/movement/config').json()['speeds']['run'] == 100

@pytest.mark.parametrize('mode', ['walk', 'run'])
def test_extreme_speed_sweeps_collision_and_neutral_input(system, monkeypatch, mode):
    c, sessions = system
    headers, person = register(c)
    onboard(c, headers)
    admin = owner(c, sessions)
    assert update(c, admin, walk=100, run=100).status_code == 200
    clock = [time.time()]
    monkeypatch.setattr(world, 'time', SimpleNamespace(time=lambda: clock[0]))
    monkeypatch.setattr(world, 'APP_ENV', 'staging')
    from backend.api.geography import safe_spawn, traversable
    # Start on the open spawn road. Every accepted segment must remain traversable
    # with .2m samples matching the unchanged safe_step implementation.
    with sessions.begin() as db:
        p = db.get(Presence, person['id']); user = db.get(User, person['id'])
        p.x, p.z = safe_spawn('london'); p.motion_speed = 100; p.last_move = clock[0]
        for direction in [(1,0),(0,1),(-1,0),(0,-1)] * 10:
            before = (p.x,p.z); clock[0] += .12
            ack = world.move(world.Movement(dx=direction[0], dz=direction[1], mode=mode), user, db)
            distance = math.dist(before,(p.x,p.z))
            assert distance <= 12.000001
            steps = max(1, math.ceil(distance/.2))
            for n in range(steps+1):
                x = before[0]+(p.x-before[0])*n/steps; z = before[1]+(p.z-before[1])*n/steps
                assert traversable('london',x,z,mode), (before,(p.x,p.z),mode)
            assert ack['movement_config']['speeds'][mode] == 100
        before = (p.x,p.z); clock[0] += .12
        world.move(world.Movement(dx=0,dz=0,mode=mode), user, db)
        assert (p.x,p.z) == before and p.motion_speed == 0
