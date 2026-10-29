"""Map access corrections preserve persistent collectible identity and claims."""
import json,math
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
from sqlalchemy import select,func
from backend.tests.test_core import system,register
from backend.api.models import Collectible,Claim,Audit,Ledger
from backend.api.geography import district,traversable,terrain_position_corrections
from backend.api.world_content import prepared_points,excluded,seed_world,repair_terrain_positions


def test_corrections_are_map_bound_safe_and_keep_trail_slots():
    root=Path(__file__).resolve().parents[1]/'data'
    for city,entry in json.loads((root/'terrain-position-corrections.json').read_text()).items():
        assert terrain_position_corrections(city)==entry
        points=prepared_points(city,96)
        if 'spawn' in entry:
            assert district(city)['spawn']==entry['spawn']['new']
            assert traversable(city,*district(city)['spawn'])
        for correction in entry['trails']:
            p=points[correction['index']]
            assert p==correction['new'] and p!=correction['old']
            assert traversable(city,*p) and not traversable(city,*p,'car') and not excluded(city,*p)
        assert min(math.dist(p,q) for i,p in enumerate(points) for q in points[i+1:])>=4.99


def test_repair_is_idempotent_preserves_claims_and_operator_edits(system):
    client,sessions=system;_,user=register(client,'terrain_repair')
    city='paris';corrections=terrain_position_corrections(city)['trails'][:3]
    ids=[str(uuid5(NAMESPACE_URL,f"mylilworlds:trail:{city}:{c['index']}")) for c in corrections]
    with sessions.begin() as db:
        seed_world(db,city,'Paris')
        for id,correction in zip(ids,corrections):
            if not db.get(Collectible,id):db.add(Collectible(id=id,city=city,title='Test fruit',kind='fruit',x=correction['old'][0],z=correction['old'][1]))
        db.flush()
        items=[db.get(Collectible,id) for id in ids]
        for item,correction in zip(items,corrections):item.x,item.z=correction['old']
        items[0].claims=7
        db.add(Claim(user_id=user['id'],collectible_id=ids[0]));db.flush()
        items[1].x+=.5 # Preserve an operator edit even on an authored ID.
        items[2].origin='rotation' # Never repurpose a different origin.
        original=[(i.x,i.z) for i in items]
        ledger=list(db.scalars(select(Ledger.id)))
        claims=list(db.scalars(select(Claim.id)))
        before=db.scalar(select(func.count()).select_from(Audit).where(Audit.action=='world.terrain_position_repaired',Audit.target==ids[0]))
        repair_terrain_positions(db,city);db.flush()
        repair_terrain_positions(db,city);db.flush()
        assert [items[0].x,items[0].z]==corrections[0]['new']
        assert items[0].claims==7 and items[0].id==ids[0]
        assert [(i.x,i.z) for i in items[1:]]==original[1:]
        assert list(db.scalars(select(Ledger.id)))==ledger
        assert list(db.scalars(select(Claim.id)))==claims
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action=='world.terrain_position_repaired',Audit.target==ids[0]))==before+1
