"""Read-only, reproducible inventory of the bundled Whitehouse rendering inputs.

This is source coverage, not a street survey or proof of browser visibility.
No coordinates, map features, collision data or rewards are changed.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inventory(root=ROOT):
    data = root / 'backend/data'
    raw = (data / 'milton-keynes.json.gz').read_bytes()
    geo = json.loads(gzip.decompress(raw))
    features = list(geo['features'])
    ids = {str(f['id']) for f in features}
    enrichment = json.loads((data / 'business-enrichment.json').read_text())
    features += [f for f in enrichment.get('milton-keynes', {}).get('buildings', [])
                 if str(f['id']) not in ids]
    correction_path = data / 'terrain-position-corrections.json'
    if correction_path.exists():
        correction = json.loads(correction_path.read_text()).get('milton-keynes', {})
        if correction.get('map_sha256') == hashlib.sha256(raw).hexdigest():
            spawn = correction.get('spawn', {})
            if geo['spawn'] == spawn.get('old'):
                geo['spawn'] = spawn['new']
    rows = []
    details = 0
    counts = collections.Counter()
    for f in features:
        tags, points = f['tags'], f['points']
        building = bool(tags.get('building'))
        eligible = building and len(points) >= 4
        # WorldScenery excludes the closing point when locating a building.
        ring = points[:-1] if eligible else points
        if not ring:
            continue
        x = sum(p[0] for p in ring) / len(ring)
        z = sum(p[1] for p in ring) / len(ring)
        near = math.hypot(x-geo['spawn'][0], z-geo['spawn'][1]) < 450
        detailed = eligible and near and details <= 700
        if eligible and near:
            details += 1
        category = next((f'{k}:{tags[k]}' for k in
                         ('building', 'shop', 'amenity', 'highway', 'leisure',
                          'natural', 'landuse', 'barrier', 'waterway') if tags.get(k)), 'other')
        counts[category] += 1
        unknown = tags.get('building') == 'yes'
        closed = bool(points and points[0] == points[-1]) if building else None
        rows.append({
            'id': str(f['id']), 'category': category,
            'world_metres': {'x': round(x, 3), 'z': round(z, 3)},
            'source': geo['source'], 'licence': geo['license'],
            'source_retrieved': geo['retrieved'],
            'render_input_status': 'eligible-footprint' if eligible else
                                   'invalid-footprint' if building else 'mapped-feature',
            'existing_spawn_detail_eligible': bool(detailed),
            'closed_ring': closed,
            'gaps': (['building-use-unspecified'] if unknown else []) +
                    (['height-approximated'] if building and not
                     any(tags.get(k) for k in ('height', 'building:levels')) else []) +
                    (['outside-spawn-detail-budget'] if eligible and not detailed else []) +
                    (['invalid-ring'] if building and not closed else []),
            'proposed_asset': 'footprint-aligned-regional-archetype' if eligible
                              else 'mapped-prop-review',
            'confidence': 'footprint-source-backed; architectural-detail-unsurveyed'
                          if eligible else 'source-tag-only',
            'implementation_result': 'existing-input; cinematic-upgrade-not-implemented',
        })
    buildings = [r for r in rows if r['category'].startswith('building:')]
    return {
        'city': 'milton-keynes', 'district': 'Whitehouse',
        'dataset_sha256': hashlib.sha256(raw).hexdigest(),
        'scope': 'Entire bundled district; no external survey or current OSM comparison',
        'measurement': 'Static renderer eligibility; actual visibility requires browser acceptance',
        'counts': {
            'features': len(features), 'building_footprints': len(buildings),
            'eligible_building_footprints': sum(r['render_input_status'] == 'eligible-footprint' for r in buildings),
            'spawn_detail_eligible': sum(r['existing_spawn_detail_eligible'] for r in buildings),
            'unknown_building_use': sum('building-use-unspecified' in r['gaps'] for r in buildings),
            'invalid_rings': sum('invalid-ring' in r['gaps'] for r in buildings),
            'duplicate_feature_ids': len(features)-len({str(f['id']) for f in features}),
            'new_buildings_added': 0,
        },
        'categories': dict(sorted(counts.items())), 'inventory': rows,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['counts'], indent=2))
