import time
from sqlalchemy import select, func
from backend.tests.test_core import system, register, onboard
from backend.api import collectible_rotation as rotation
from backend.api.expansion import Destination
from backend.api.models import Presence, Claim, Ledger


def test_every_active_world_replenishes_and_fruit_gem_rewards_reconcile(system):
    c, dbs=system
    h,u=register(c,'availability_player');onboard(c,h)
    with dbs() as db:
        cities=list(db.scalars(select(Destination.id).where(Destination.status=='ACTIVE',Destination.public==True,Destination.joinable==True)))
        assert cities
        now=time.time()
        for city in cities:
            wave=rotation.wave(db,city,now)
            assert 0<len(wave)<=rotation.settings(db)['density']
            assert {'fruit','gem'}<={i.kind for i in wave}
            next_wave=rotation.wave(db,city,now+rotation.settings(db)['refresh_minutes']*60)
            assert {i.id for i in wave}.isdisjoint(i.id for i in next_wave)
    before=c.get('/api/wallet',headers=h).json()
    expected_xp=expected_credits=0
    for kind in ['fruit','gem']:
        with dbs.begin() as db:
            item=next(i for i in rotation.wave(db,'london') if i.kind==kind)
            p=db.get(Presence,u['id']);p.x=item.x;p.z=item.z;p.updated_at=time.time()
            # Local test clock spacing only; no staging claims are changed.
            for claim in db.scalars(select(Claim).where(Claim.user_id==u['id'])):claim.created_at-=10
        r=c.post('/api/collectibles/'+item.id+'/claim',headers=h)
        assert r.status_code==200,r.text
        assert r.json()['awarded_xp']>0
        expected_xp+=r.json()['awarded_xp'];expected_credits+=r.json()['awarded_credits']
        again=c.post('/api/collectibles/'+item.id+'/claim',headers=h).json()
        assert again['awarded_xp']==again['awarded_credits']==0
    after=c.get('/api/wallet',headers=h).json()
    assert after['xp']-before['xp']==expected_xp
    assert after['credits']-before['credits']==expected_credits
    with dbs() as db:
        assert db.scalar(select(func.count()).select_from(Claim).where(Claim.user_id==u['id']))==2
        assert db.scalar(select(func.sum(Ledger.amount)).where(Ledger.user_id==u['id'],Ledger.currency=='xp'))==after['xp']
