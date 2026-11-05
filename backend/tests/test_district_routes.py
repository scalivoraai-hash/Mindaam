"""Reproduce connected return routes through the real shared swept collision model."""
import json
import math
from pathlib import Path

import pytest

from backend.api.geography import district, safe_spawn, safe_step, traversable

FIXTURES = Path(__file__).resolve().parents[2] / 'scripts/tests'
ROUTES = [route for filename in ('district-routes.json', 'district-browser-routes.json')
          for route in json.loads((FIXTURES / filename).read_text())]


@pytest.mark.parametrize('route', ROUTES, ids=lambda route: route['city'])
def test_connected_outdoor_return_route(route):
    city = route['city']
    start = safe_spawn(city)
    assert math.dist(start, route['start']) < .001
    position = start
    travelled = 0.
    turns = route['turns']
    for target in turns[1:] + turns[-2::-1]:
        dx, dz = target[0] - position[0], target[1] - position[1]
        position = safe_step(city, *position, dx, dz)
        assert math.dist(position, target) < .001, (city, target, position)
        travelled += math.hypot(dx, dz)
    assert travelled == pytest.approx(route['round_trip_m'], abs=.01)
    assert travelled >= 500 and math.dist(start, route['destination']) >= 250
    assert math.dist(start, position) < .001
    assert not traversable(city, district(city)['radius'] + 50, 0)
