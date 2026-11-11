"""Property discovery follows mapped footprints, not a single rear-wall anchor."""
import math
from unittest.mock import patch
from uuid import uuid4

from backend.api.civic import entrance
from backend.api.property_inventory import facade_grid, inventory, nearby
from backend.tests.test_property_economy import explorer, system


def test_soho_hotel_is_discoverable_from_its_authorized_visit_point():
    item = inventory('london')['london:184419081']
    target = entrance('london', (item['x'], item['z']))
    assert target is not None
    assert math.dist(target, (item['x'], item['z'])) > 32
    assert item['id'] in {row['id'] for row in nearby('london', *target)}


def test_visit_snapshot_includes_persisted_owned_name(system):
    client, sessions = system
    headers, owner = explorer(client, sessions, 'frontageowner', 2000)
    key = 'london:184419081'
    catalogue = client.get('/api/properties/city/london', headers=headers)
    assert catalogue.status_code == 200, catalogue.text
    claim = client.post('/api/properties/'+key+'/claim', headers=headers,
                        json={'amount': 2000, 'request_key': str(uuid4())})
    assert claim.status_code == 200, claim.text
    name = 'My Soho Residence'
    saved = client.patch('/api/properties/'+key+'/studio', headers=headers,
                         json={'name': name, 'board': 'forest'})
    assert saved.status_code == 200, saved.text
    visit = client.post('/api/places/travel/visit', headers=headers,
                        json={'city': 'london', 'place_id': 'property:'+key})
    assert visit.status_code == 200, visit.text
    row = next(p for p in visit.json()['properties'] if p['id'] == key)
    assert row['name'] == name and row['owned'] is True


def test_large_footprint_near_edge_is_found_without_extending_range():
    city = 'discovery-test'
    row = dict(id=city+':wide', x=100, z=50)
    footprint = ((0, 0), (100, 0), (100, 100), (0, 100), (0, 0))
    facade_grid.cache_clear()
    try:
        with patch('backend.api.property_inventory.inventory', return_value={row['id']: row}), patch(
            'backend.api.property_inventory.outlines', return_value={row['id']: footprint}
        ):
            assert nearby(city, -31, 50) == [row]
            assert nearby(city, -33, 50) == []
    finally:
        facade_grid.cache_clear()


def test_nearby_keeps_eight_property_bound_and_deduplicates_grid_cells():
    city = 'discovery-test'
    rows = {f'{city}:{i}': dict(id=f'{city}:{i}', x=100, z=i) for i in range(12)}
    shapes = {key: ((0, i), (100, i), (100, i+1), (0, i+1), (0, i))
              for i, key in enumerate(rows)}
    facade_grid.cache_clear()
    try:
        with patch('backend.api.property_inventory.inventory', return_value=rows), patch(
            'backend.api.property_inventory.outlines', return_value=shapes
        ):
            found = nearby(city, -1, 0)
            assert len(found) == len({r['id'] for r in found}) == 8
            assert [r['id'] for r in found] == list(rows)[:8]
    finally:
        facade_grid.cache_clear()
