import math
import pytest
from backend.api import geography as g, terrain as t


def polygon(tags, x=10, z=-10, size=30, holes=None):
    return {'tags': tags, 'points': [[x,z],[x+size,z],[x+size,z+size],[x,z+size],[x,z]], 'holes': holes or []}


@pytest.fixture
def public_ground(monkeypatch):
    features = [
        {'tags': {'highway': 'residential'}, 'points': [[0,-30],[0,30]]},
        polygon({'leisure': 'park'}, 4, -20, 40),
        polygon({'building': 'yes'}, 18, 0, 5),
        polygon({'access': 'private', 'landuse': 'grass'}, 28, 0, 5),
        polygon({'natural': 'water'}, 18, -15, 5),
        {'tags': {'barrier': 'fence'}, 'points': [[10,-15],[10,-5]]},
    ]
    monkeypatch.setattr(g, 'district', lambda city: {'radius':50,'features':features,'spawn':[0,0],'origin':{'lat':51.5,'lon':-.1}})
    from backend.api import grand_arena
    monkeypatch.setattr(grand_arena, 'traversable_plaza', lambda *args: False)
    for fn in [t.navigation,t.grid,g.collision_grid,g.street_grid,g.road_segments,g.driving_segments,g.safe_spawn]:fn.cache_clear()
    yield
    for fn in [t.navigation,t.grid,g.collision_grid,g.street_grid,g.road_segments,g.driving_segments,g.safe_spawn]:fn.cache_clear()


def test_road_to_park_continuous_and_back(public_ground):
    for mode in ['walk','run']:
        assert g.safe_step('test',0,0,15,0,mode)==pytest.approx((15,0))
        assert g.safe_step('test',15,0,-15,0,mode)==pytest.approx((0,0))
        assert g.safe_step('test',5,5,6,6,mode)==pytest.approx((11,11))
    assert not g.traversable('test',15,0,'car')
    assert not g.traversable('test',15,0,'bike')
    assert not g.traversable('test',15,0,'scooter')


def test_blocked_ground_fence_and_bounds(public_ground):
    for point in [(20,2),(30,2),(20,-12),(10,-10),(51,0),(-20,20),(math.nan,0)]:
        assert not g.traversable('test',*point)
    x,z=g.safe_step('test',8,-10,5,0)
    assert x<9.66 and z==-10
    x,z=g.safe_step('test',16,2,10,0)
    assert x<18


def test_access_and_holes():
    assert t.classification(polygon({'leisure':'garden'})) is None
    assert t.classification(polygon({'leisure':'garden','access':'yes'}))=='public'
    assert t.classification(polygon({'leisure':'park','access':'private'}))=='blocked'
    assert t.classification(polygon({'landuse':'farmland'})) is None
    assert t.classification({'tags':{'leisure':'park'},'points':[[0,0],[10,0],[10,10]]}) is None


@pytest.mark.parametrize('city',['milton-keynes','london','new-york','abu-dhabi'])
def test_real_public_ground_and_buildings(city):
    nav=t.navigation(city)
    candidates=[]
    for f in nav['features']:
        if f['kind']!='public':continue
        p=f['points'];lo=[min(a[i] for a in p) for i in [0,1]];hi=[max(a[i] for a in p) for i in [0,1]]
        for ix in range(1,10):
            for iz in range(1,10):
                x=lo[0]+(hi[0]-lo[0])*ix/10;z=lo[1]+(hi[1]-lo[1])*iz/10
                if abs(x)<=nav['radius'] and abs(z)<=nav['radius'] and t.permits(city,x,z) and not t.permits(city,x,z,False):candidates.append((x,z))
    assert candidates, f'{city} must expose real mapped public ground beyond road strips'
    assert all(g.traversable(city,*p) for p in candidates[:20])
    for f in g.district(city)['features']:
        if not f['tags'].get('building'):continue
        p=f['points'];x=sum(a[0] for a in p)/len(p);z=sum(a[1] for a in p)/len(p)
        if g.inside_building(city,x,z):assert not g.traversable(city,x,z)

from backend.tests.test_core import system, register, onboard


def test_authenticated_movement_crosses_road_edge(system, monkeypatch):
    from backend.api import world
    from backend.api.models import Presence
    from types import SimpleNamespace
    import time
    client,sessions=system
    headers,user=register(client,'publicgroundqa');onboard(client,headers)
    import json
    from pathlib import Path
    start=json.loads((Path(__file__).resolve().parents[2]/'scripts/tests/public-terrain-crossings.json').read_text())['london']['start']
    now=[time.time()]
    monkeypatch.setattr(world,'APP_ENV','staging')
    monkeypatch.setattr(world,'time',SimpleNamespace(time=lambda:now[0]))
    with sessions.begin() as db:
        p=db.get(Presence,user['id']);p.x,p.z=start;p.last_move=now[0];p.motion_speed=0
    for _ in range(48):
        now[0]+=.12
        response=client.post('/api/world/move',headers=headers,json={'dx':math.cos(.7),'dz':-math.sin(.7),'mode':'walk'})
        assert response.status_code==200,response.text
    position=response.json()
    assert math.hypot(position['x']-start[0],position['z']-start[1])>12
    assert t.permits('london',position['x'],position['z'])
    assert not t.permits('london',position['x'],position['z'],open_ground=False)
    with sessions() as db:
        p=db.get(Presence,user['id']);assert p.x==pytest.approx(position['x'])
