"""Virtual property inventory derived from installed mapped building footprints."""
from functools import lru_cache
import math
from .geography import district

CATEGORIES = {
    'house': 'house', 'detached': 'house', 'semidetached_house': 'house',
    'terrace': 'townhouse', 'apartments': 'apartments', 'residential': 'residential',
    'villa': 'villa', 'retail': 'shop', 'commercial': 'commercial', 'office': 'office',
}
EXCLUDED = {'hospital', 'school', 'college', 'university', 'fire_station', 'police',
            'place_of_worship', 'kindergarten', 'prison', 'clinic', 'townhall'}

@lru_cache(maxsize=64)
def inventory(city):
    geo = district(city)
    rows = {}
    for feature in geo['features']:
        tags = feature['tags']
        building = tags.get('building')
        if not building or tags.get('amenity') in EXCLUDED or tags.get('access') in {'no', 'private'}:
            continue
        category = CATEGORIES.get(building)
        if not category and building == 'yes':
            category = 'shop' if tags.get('shop') else 'office' if tags.get('office') else 'building'
        points = feature.get('points', [])
        if not category or len(points) < 4 or not feature.get('id'):
            continue
        edges = list(zip(points, points[1:] + points[:1]))
        area = abs(sum(a[0]*b[1] - b[0]*a[1] for a,b in edges)) / 2
        if area < 12:
            continue
        # A facade anchor lies on the existing footprint, including concave buildings.
        a,b = max(edges, key=lambda edge: math.dist(*edge))
        x,z = (a[0]+b[0])/2, (a[1]+b[1])/2
        if max(abs(x), abs(z)) > geo['radius']:
            continue
        key = f"{city}:{feature['id']}"
        if key in rows:
            raise ValueError(f'Duplicate mapped property: {key}')
        rows[key] = dict(id=key, city=city, category=category, title=tags.get('name', category.title())[:120],
                         x=x, z=z)
    return rows

@lru_cache(maxsize=64)
def facade_grid(city):
    cells = {}
    for row in inventory(city).values():
        cells.setdefault((math.floor(row['x']/32),math.floor(row['z']/32)),[]).append(row)
    return cells

def nearby(city,x,z):
    cells=facade_grid(city)
    ix,iz=math.floor(x/32),math.floor(z/32)
    rows=[row for a in range(ix-1,ix+2) for b in range(iz-1,iz+2) for row in cells.get((a,b),[])
          if math.hypot(row['x']-x,row['z']-z)<=32]
    return sorted(rows,key=lambda row:math.hypot(row['x']-x,row['z']-z))[:8]
