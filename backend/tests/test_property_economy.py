from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy import select
from backend.tests.test_core import system,register,onboard
from backend.api.economy import credit,balance
from backend.api.property_economy import Trade,Property,Offer
from backend.api.locations import CITIES
from backend.api.property_inventory import inventory

def explorer(c,sessions,name,xp):
    h,u=register(c,name)
    onboard(c,h)
    with sessions.begin() as db:
        credit(db,u['id'],xp-balance(db,u['id'],'xp'),'test','property-test',str(uuid4()),'xp')
    return h,u

def cities_test_rows():
    return [inventory(c['id']) for c in CITIES]

def test_every_installed_map_has_distinct_inventory():
    maps=cities_test_rows()
    ids=[key for rows in maps for key in rows]
    assert all(maps) and len(ids)==len(set(ids))

def test_purchase_and_competing_offers(system):
    c,sessions=system
    a,alice=explorer(c,sessions,'alice',4000)
    b,bob=explorer(c,sessions,'bob',3000)
    d,dan=explorer(c,sessions,'dan',3000)
    items=c.get('/api/properties/city/london',headers=a).json()['items']
    def post(key,action,h,body):
        return c.post('/api/properties/'+key+'/'+action,headers=h,json=body)
    key,second=[r['id'] for r in items[:2]]
    req={'amount':2000,'request_key':str(uuid4())}
    r=post(key,'claim',a,req)
    assert r.status_code==200,r.text
    assert post(key,'claim',a,req).json()==r.json()
    assert post(second,'claim',a,{**req,'request_key':str(uuid4())}).json()['balance']==0
    short=post(items[2]['id'],'claim',a,{**req,'request_key':str(uuid4())})
    assert short.json()['detail']['shortfall']==2000
    assert len(c.get('/api/properties/portfolio',headers=a).json())==2
    studio={'name':'Sera Villa','board':'forest'}
    url='/api/properties/'+key+'/studio'
    assert c.patch(url,headers=b,json=studio).status_code==403
    assert c.patch(url,headers=a,json=studio).json()['name']=='Sera Villa'
    bids=[post(key,'offer',h,{'amount':3000}).json()['id'] for h in (b,d)]
    decide='/api/properties/offers/'+bids[0]
    assert c.post(decide,headers=a,json={'action':'counter','amount':2900,'expected_amount':3000}).status_code==200
    assert c.post(decide,headers=b,json={'action':'accept','expected_amount':3000}).status_code==409
    assert c.post(decide,headers=b,json={'action':'accept','expected_amount':2900}).json()['state']=='accepted'
    assert c.post(decide,headers=b,json={'action':'accept','expected_amount':2900}).status_code==409
    with sessions() as db:
        assert db.get(Property,key).owner==bob['id']
        assert db.get(Offer,bids[1]).state=='superseded'
        assert balance(db,bob['id'],'xp')==100
        assert balance(db,alice['id'],'xp')==2900
        assert len(db.scalars(select(Trade)).all())==3
    assert c.patch(url,headers=a,json=studio).status_code==403

def test_concurrent_buyers(system):
    c,sessions=system
    users=[explorer(c,sessions,name,2000) for name in ('alice','bob')]
    key=c.get('/api/properties/city/london',headers=users[0][0]).json()['items'][0]['id']
    def claim(user):
        return c.post(f'/api/properties/{key}/claim',headers=user[0],json={'amount':2000,'request_key':str(uuid4())}).status_code
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(claim,users))==[200,409]
    with sessions() as db:
        assert len(db.scalars(select(Trade)).all())==1
        assert sorted(balance(db,u['id'],'xp') for _,u in users)==[0,2000]
