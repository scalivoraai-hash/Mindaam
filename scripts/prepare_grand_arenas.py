"""Regenerate reviewed placements locally after installed geography/trails change."""
import hashlib,json
from pathlib import Path
from backend.api.locations import CITIES
from backend.api.grand_arena import placement
root=Path(__file__).resolve().parents[1]/'backend/data'
placements={}
for city in CITIES:
 row=placement(city['id'])
 if not row:raise RuntimeError('No safe Grand Arena location: '+city['id'])
 row={**row,'source_hash':hashlib.sha256((root/(city['id']+'.json.gz')).read_bytes()+(root/'business-enrichment.json').read_bytes()+(root/'world-trails.json').read_bytes()).hexdigest()}
 placements[city['id']]=row
 print(city['id'],flush=True)
(root/'arena-placements.json').write_text(json.dumps(placements,indent=2)+'\n')
print('Prepared',len(placements),'cities')
