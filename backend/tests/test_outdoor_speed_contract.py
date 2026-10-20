"""Actual movement integration with controlled server time, independent of CI speed."""
import math
from types import SimpleNamespace

import pytest
from backend.tests.test_core import system, register, onboard
from backend.api import world
from backend.api.models import Presence, User


@pytest.mark.parametrize('mode,strength', [('walk', .6), ('run', 1)])
@pytest.mark.parametrize('gaps', [(.12,) * 8, (.12, .35, .12, .8, .12, .12)])
def test_outdoor_speed_contract(system, monkeypatch, mode, strength, gaps):
    client, sessions = system
    headers, user = register(client)
    onboard(client, headers)
    assert world.MOVEMENT['normalWorldMultiplier'] == 3
    assert world.RUN_SPEED / world.WALK_SPEED == pytest.approx(1.875)
    clock = [1000.]
    monkeypatch.setattr(world, 'time', SimpleNamespace(time=lambda: clock[0]))

    def integrate(multiplier):
        monkeypatch.setitem(world.MOVEMENT, 'normalWorldMultiplier', multiplier)
        clock[0] = 1000.
        distances = []
        with sessions.begin() as db:
            player = db.get(Presence, user['id'])
            account = db.get(User, user['id'])
            player.zone_id = 'world'
            player.motion_speed = 0
            player.last_move = clock[0]
            for gap in gaps:
                # Keep the open test road; preserve acceleration and elapsed state.
                player.x = player.z = 0
                clock[0] += gap
                result = world.move(world.Movement(dx=strength, dz=0, mode=mode), account, db)
                distances.append(math.hypot(result['x'], result['z']))
        return distances

    previous = integrate(1)
    upgraded = integrate(3)
    assert all(distance > 0 for distance in previous)
    assert upgraded == pytest.approx([distance * 3 for distance in previous])
    if max(gaps) > .5:
        # Reproduce why wall-clock benchmarking cannot prove the multiplier:
        # delayed ticks intentionally lose time to the cap and idle reset.
        base = world.RUN_SPEED if mode == 'run' else world.WALK_SPEED
        assert sum(upgraded) / sum(gaps) < base * strength * 2.8
