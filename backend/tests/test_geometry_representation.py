"""Static geometry must retain wire values without cyclic-GC point lists."""
import gc
import gzip
import json
from pathlib import Path
from starlette.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from backend.api.geography import district, geometry
from backend.api.locations import CITIES

def test_all_installed_coordinate_values_unchanged_and_untracked():
    root=Path(__file__).resolve().parents[1]/'data'
    maps=[district(city['id']) for city in CITIES]
    # Tuple containers become untracked after their numeric children are scanned.
    for _ in range(3):gc.collect()
    for city,loaded in zip(CITIES,maps):
        source=json.loads(gzip.decompress((root/(city['id']+'.json.gz')).read_bytes()))
        features={str(f['id']):f for f in loaded['features']}
        for original in source['features']:
            cached=features[str(original['id'])]
            assert json.loads(json.dumps(cached['points']))==original['points'],city['id']
            assert json.loads(json.dumps(cached.get('holes',[])))==original.get('holes',[]),city['id']
        for feature in loaded['features']:
            assert not gc.is_tracked(feature['points']),city['id']
            assert all(not gc.is_tracked(p) for p in feature['points']),city['id']
            for ring in feature.get('holes',[]):
                assert not gc.is_tracked(ring)
                assert all(not gc.is_tracked(p) for p in ring)

def test_geography_response_has_identical_json_without_loop_encoding():
    from backend.api.terrain import navigation
    from backend.api.street_vehicles import placements
    from backend.api.grand_arena import placement
    city='milton-keynes'
    geo=district(city);arena=placement(city)
    radius=max(geo['radius'],max(abs(arena['x']),abs(arena['z']))+25) if arena else geo['radius']
    original={**geo,'radius':radius,'navigation':navigation(city),'arena':arena,'street_vehicles':placements(city)}
    response=geometry(city)
    assert isinstance(response,JSONResponse)
    assert response.body==JSONResponse(jsonable_encoder(original)).body
    assert response.status_code==200
