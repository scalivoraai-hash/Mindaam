"""Virtual property inventory derived from installed mapped building footprints."""

from functools import lru_cache
import math
from .geography import district

CATEGORIES = {
    "house": "house",
    "detached": "house",
    "semidetached_house": "house",
    "terrace": "townhouse",
    "apartments": "apartments",
    "residential": "residential",
    "villa": "villa",
    "retail": "shop",
    "commercial": "commercial",
    "office": "office",
}
EXCLUDED = {
    "hospital",
    "school",
    "college",
    "university",
    "fire_station",
    "police",
    "place_of_worship",
    "kindergarten",
    "prison",
    "clinic",
    "townhall",
}


@lru_cache(maxsize=64)
def inventory(city):
    geo = district(city)
    rows = {}
    for feature in geo["features"]:
        tags = feature["tags"]
        building = tags.get("building")
        if (
            not building
            or tags.get("amenity") in EXCLUDED
            or tags.get("access") in {"no", "private"}
        ):
            continue
        category = CATEGORIES.get(building)
        if not category and building == "yes":
            category = (
                "shop"
                if tags.get("shop")
                else "office"
                if tags.get("office")
                else "building"
            )
        points = feature.get("points", [])
        if not category or len(points) < 4 or not feature.get("id"):
            continue
        edges = list(zip(points, points[1:] + points[:1]))
        area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in edges)) / 2
        if area < 12:
            continue
        # A facade anchor lies on the existing footprint, including concave buildings.
        a, b = max(edges, key=lambda edge: math.dist(*edge))
        x, z = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if max(abs(x), abs(z)) > geo["radius"]:
            continue
        key = f"{city}:{feature['id']}"
        if key in rows:
            raise ValueError(f"Duplicate mapped property: {key}")
        rows[key] = dict(
            id=key,
            city=city,
            category=category,
            title=tags.get("name", category.title())[:120],
            x=x,
            z=z,
        )
    from .grand_arena import placement

    arena = placement(city)
    if arena:
        key = city + ":venue-arena"
        rows[key] = dict(
            id=key,
            city=city,
            category="venue",
            title=arena["name"],
            x=arena["x"],
            z=arena["z"],
        )
    return rows


@lru_cache(maxsize=64)
def facade_grid(city):
    cells = {}
    shapes = outlines(city)
    for row in inventory(city).values():
        points = shapes.get(row['id']) or ((row['x'], row['z']),)
        # Large/concave buildings can have a rear anchor farther than the
        # discovery radius from their public approach. Index the footprint.
        for ix in range(math.floor(min(p[0] for p in points) / 32),
                        math.floor(max(p[0] for p in points) / 32) + 1):
            for iz in range(math.floor(min(p[1] for p in points) / 32),
                            math.floor(max(p[1] for p in points) / 32) + 1):
                cells.setdefault((ix, iz), []).append(row)
    return cells


def nearby(city, x, z):
    cells = facade_grid(city)
    ix, iz = math.floor(x / 32), math.floor(z / 32)
    rows = {
        row['id']: row
        for a in range(ix - 1, ix + 2)
        for b in range(iz - 1, iz + 2)
        for row in cells.get((a, b), [])
    }
    shapes = outlines(city)
    def distance(row):
        points = shapes.get(row['id'])
        if not points:
            return math.hypot(row['x'] - x, row['z'] - z)
        nearest = math.inf
        for a, b in zip(points, points[1:] + points[:1]):
            dx, dz = b[0] - a[0], b[1] - a[1]
            t = max(0, min(1, ((x-a[0])*dx + (z-a[1])*dz) / (dx*dx+dz*dz or 1)))
            nearest = min(nearest, math.hypot(x-a[0]-t*dx, z-a[1]-t*dz))
        return nearest
    ranked = sorted((distance(row), key) for key, row in rows.items())
    return [rows[key] for d, key in ranked if d <= 32][:8]


@lru_cache(maxsize=64)
def outlines(city):
    return {
        f"{city}:{f['id']}": f["points"]
        for f in district(city)["features"]
        if f.get("id") and f["tags"].get("building")
    }
