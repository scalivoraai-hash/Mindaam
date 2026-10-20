"""Fail on legacy public branding; allow only documented durable/internal identifiers."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
ALLOWED={
 'apps/consumer-web/package.json': ['@pulseworld/web'],
 'backend/api/db.py':['pulseworld-local.db'],
 'backend/api/commerce.py':['pulseworld-payment:'],
 'backend/api/world_content.py':['mylilworlds:trail:','mylilworlds:mission:'],
 'backend/api/collectible_rotation.py':['mylilworlds:rotation:v1:'],
 'backend/api/business_spatial.py':['mylilworlds:'],
}
failed=[]
for folder in ['apps/consumer-web/app','apps/consumer-web/components','apps/consumer-web/lib','apps/consumer-web/public','backend/api']:
 for p in (ROOT/folder).rglob('*'):
  if not p.is_file() or p.suffix not in {'.tsx','.ts','.js','.svg','.webmanifest','.json','.py','.css'}:continue
  text=p.read_text();path=str(p.relative_to(ROOT))
  text=re.sub(r'logging.getLogger\([\'\"]pulseworld(?:\.[^\'\"]*)?[\'\"]\)','INTERNAL_LOGGER',text)
  for value in ALLOWED.get(path,[]):text=text.replace(value,'INTERNAL_IDENTIFIER')
  hits=re.findall(r'MyLilWorlds|PulseWorld|My<span>Lil</span>Worlds',text,re.I)
  if hits:failed.append(f'{path}: {sorted(set(hits))}')
if failed:raise SystemExit('\n'.join(failed))
print('PASS: zero old product names in audited user-facing source/assets; approved internal exceptions retained.')
