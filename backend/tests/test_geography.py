import importlib
import pytest
from backend.api.geography import district, walkable, safe_spawn
from backend.tests.test_core import system, register, onboard
from backend.api.models import Collectible

@pytest.mark.parametrize('city',['london','birmingham','milton-keynes'])
def test_real_map_and_spawn(city):
    d=district(city)
    assert d['origin']['lat']>50
    assert walkable(city,*d['spawn'])
    assert any('building' in f['tags'] for f in d['features'])
    assert any('highway' in f['tags'] for f in d['features'])
    assert not walkable(city,351,351)


def test_mapped_enter_move_and_claim(system,monkeypatch):
    c,sessions=system
    module=importlib.import_module('backend.api.world')
    monkeypatch.setattr(module,'APP_ENV','staging')
    h,u=register(c,'mapexplorer');onboard(c,h)
    for city in ['london','birmingham','milton-keynes']:
        assert c.post(f'/api/growth/worlds/{city}/starter',headers=h,json={'confirmed':True}).status_code==200
        world=c.post('/api/world/enter',headers=h,json={'city':city}).json()
        spawn=list(safe_spawn(city))
        assert [world['position']['x'],world['position']['z']]==spawn
        moved=c.post('/api/world/move',headers=h,json={'dx':1,'dz':0,'mode':'walk'})
        assert moved.status_code==200
        assert walkable(city,moved.json()['x'],moved.json()['z'])
    # Movement distance depends on elapsed server time. Collect at the returned
    # authoritative position, not the spawn the player has already left.
    position=moved.json()
    with sessions.begin() as db:
        db.add(Collectible(id='map-trail-test',city=city,title='Trail apple',kind='fruit',x=position['x'],z=position['z']))
    result=c.post('/api/collectibles/map-trail-test/claim',headers=h,json={})
    assert result.status_code==200,result.text
    again=c.post('/api/collectibles/map-trail-test/claim',headers=h,json={})
    assert again.status_code in [200,409]
    assert c.get('/api/geography/unknown').status_code==422
