"""Bounded virtual outdoor traversal; explicit mapped restrictions take precedence."""
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
        bounds=(min(a[0] for a in p)-pad,max(a[0] for a in p)+pad,min(a[1] for a in p)-pad,max(a[1] for a in p)+pad)
        for ix in range(max(lo,math.floor(bounds[0]/32)), min(hi,math.floor(bounds[1]/32))+1):
            for iz in range(max(lo,math.floor(bounds[2]/32)), min(hi,math.floor(bounds[3]/32))+1):
                cells.setdefault((ix, iz), []).append((f,bounds))
    return cells


def permits(city, x, z, open_ground=True, buildings=True):
    from .geography import point_inside, segment_distance
    if not math.isfinite(x) or not math.isfinite(z):
        return False
    radius = navigation(city)["radius"]
    if abs(x) > radius or abs(z) > radius:
        return False
    allowed = open_ground
    for f,bounds in grid(city).get((math.floor(x/32), math.floor(z/32)), []):
        if not bounds[0]<=x<=bounds[1] or not bounds[2]<=z<=bounds[3]:
            continue
        p, kind = f['points'], f['kind']
        if kind == 'building' and not buildings or kind == 'public' and not open_ground:
            continue
        if kind == 'road':
            allowed |= any(segment_distance(x,z,a,b)<=6 for a,b in zip(p,p[1:]))
            continue
        inside = kind != 'barrier' and len(p) >= 4 and p[0] == p[-1] and point_inside(x,z,p) and not any(point_inside(x,z,h) for h in f['holes'])
        if kind == 'public':
            allowed |= inside
        elif inside or kind != 'building' and any(segment_distance(x,z,a,b)<=.35 for a,b in zip(p,p[1:])):
            return False
    return allowed
