"""Read-only current-map comparison. Never updates geography or collision data."""
import argparse
import collections
import datetime
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def compare(source):
    spec=importlib.util.spec_from_file_location('osm_import',ROOT/'scripts/import-osm.py')
    importer=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    raw=source.read_bytes()
    original=json.loads(gzip.decompress((ROOT/'backend/data/milton-keynes.json.gz').read_bytes()))
    origin=original['origin'];radius=original['radius'];old={str(f['id']):f for f in original['features']}
    fresh=importer.convert(raw,origin)
    within=lambda p:abs(p[0])<=radius and abs(p[1])<=radius
    intersects=lambda f:any(within(p) for p in f['points'])
    buildings=[f for f in fresh if f['tags'].get('building') and intersects(f)]
    new_buildings=[f for f in buildings if f['id'] not in old]
    additions=[f for f in fresh if f['id'] not in old and intersects(f)]
    known_pois=[{'id':f['id'],'tags':f['tags'],'present':f['id'] in old} for f in fresh if intersects(f) and f['tags'].get('name') and any(k in f['tags'] for k in ['shop','amenity'])]
    decorative=[]
    for node in ET.fromstring(raw).findall('node'):
        tags={t.attrib['k']:t.attrib['v'] for t in node.findall('tag')}
        point=[round((float(node.attrib['lon'])-origin['lon'])*111320*math.cos(math.radians(origin['lat'])),2),round((origin['lat']-float(node.attrib['lat']))*111320,2)]
        if not within(point):continue
        if not (tags.get('natural')=='tree' or tags.get('amenity') in ['bench','waste_basket','grit_bin','post_box'] or tags.get('highway') in ['bus_stop','crossing','street_lamp']):continue
        safe={k:v for k,v in tags.items() if k in ['natural','amenity','highway','name','crossing','crossing:markings','direction','height','species','leaf_type']}
        id=str(2000000000000+int(node.attrib['id']))
        decorative.append({'id':id,'osm_type':'node','osm_id':node.attrib['id'],'tags':safe,'points':[point],'existing_feature':id in old,'status':'mapped candidate; placement/render acceptance pending'})
    counts=collections.Counter()
    for f in additions:
        tags=f['tags'];category=next((k+':'+tags[k] for k in ['building','barrier','landuse','waterway','highway','natural','amenity','shop'] if k in tags),'other')
        counts[category]+=1
    return {
        'city':'milton-keynes','audit_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source':'OpenStreetMap contributors','licence':'ODbL 1.0','source_url':'https://www.openstreetmap.org/copyright',
        'source_sha256':hashlib.sha256(raw).hexdigest(),'original_buildings':sum(bool(f['tags'].get('building')) for f in old.values()),
        'current_extract_building_rings_with_vertex_in_supported_square':len(buildings),'new_verified_building_ids':len(new_buildings),
        'new_building_candidates':new_buildings,'other_new_feature_categories':dict(counts),'named_pois':known_pois,
        'decorative_node_candidates':decorative,
        'limitations':['OSM coverage is not a street survey. Zero new building IDs does not prove every real building is mapped.',
                      'The map API returns intersecting ways and partial relations; retain existing outside/partial geometry.',
                      'Polygon inclusion is a vertex-based candidate filter, not exact polygon/square clipping.',
                      'No source file, gameplay data, collision boundary or database was modified. Candidates are not implemented assets.'],
    }


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=compare(args.source)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['original_buildings','current_extract_building_rings_with_vertex_in_supported_square','new_verified_building_ids','other_new_feature_categories']}))
