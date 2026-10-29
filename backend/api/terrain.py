"""Conservative OSM pedestrian coverage; no inferred access to unmapped land."""
import math
from functools import lru_cache

PUBLIC = {'yes', 'designated', 'permissive', 'public'}
RESTRICTED = {'no', 'private', 'customers', 'permit', 'agricultural', 'forestry'}


def pedestrian_access(tags):
    return tags.get('foot', tags.get('access', ''))


def closed(feature):
    p = feature['points']
    return len(p) >= 4 and p[0] == p[-1]


def classification(feature):
    t = feature['tags']
    access = pedestrian_access(t)
    if t.get('building'):
        return 'building'
    if access in RESTRICTED or t.get('natural') in {'water', 'wetland', 'cliff', 'scree', 'bare_rock'} or t.get('waterway') or t.get('landuse') in {'construction', 'military', 'quarry'} or t.get('leisure') == 'swimming_pool':
        return 'blocked'
    if t.get('barrier') and t['barrier'] not in {'entrance', 'cattle_grid'}:
        return 'barrier'
    if t.get('highway') and t['highway'] not in {'motorway', 'motorway_link', 'trunk', 'trunk_link', 'construction', 'proposed'}:
        return 'road'
    if closed(feature) and (t.get('leisure') in {'park', 'recreation_ground', 'playground', 'dog_park'} or t.get('landuse') in {'grass', 'recreation_ground', 'village_green'} or t.get('natural') == 'grassland' or (access in PUBLIC and (t.get('leisure') in {'garden', 'pitch'} or t.get('landuse') in {'meadow', 'forest'} or t.get('natural') in {'wood', 'scrub'}))):
        return 'public'
    return None


@lru_cache(maxsize=64)
def navigation(city):
    from .geography import district
    d = district(city)
    return {'radius': d['radius'], 'features': [dict(kind=kind, points=f['points'], holes=f.get('holes', [])) for f in d['features'] if (kind := classification(f))]}


@lru_cache(maxsize=64)
def grid(city):
    cells = {}
    nav = navigation(city)
    lo, hi = math.floor(-nav['radius']/32), math.floor(nav['radius']/32)
    for f in nav['features']:
        p = f['points']
        if not p:
            continue
        pad = 6 if f['kind'] == 'road' else .35
        for ix in range(max(lo,math.floor((min(a[0] for a in p)-pad)/32)), min(hi,math.floor((max(a[0] for a in p)+pad)/32))+1):
            for iz in range(max(lo,math.floor((min(a[1] for a in p)-pad)/32)), min(hi,math.floor((max(a[1] for a in p)+pad)/32))+1):
                cells.setdefault((ix, iz), []).append(f)
    return cells


def permits(city, x, z, open_ground=True, buildings=True):
    from .geography import point_inside, segment_distance
    if not math.isfinite(x) or not math.isfinite(z):
        return False
    allowed = False
    for f in grid(city).get((math.floor(x/32), math.floor(z/32)), []):
        p, kind = f['points'], f['kind']
        inside = len(p) >= 4 and p[0] == p[-1] and point_inside(x, z, p) and not any(point_inside(x, z, h) for h in f['holes'])
        near = any(segment_distance(x, z, a, b) <= (6 if kind == 'road' else .35) for a, b in zip(p, p[1:]))
        if (kind in {'blocked', 'barrier'} or kind == 'building' and buildings) and ((near and kind != 'building') or (inside and kind in {'blocked','building'})):
            return False
        allowed |= kind == 'road' and near or open_ground and kind == 'public' and inside
    return allowed
