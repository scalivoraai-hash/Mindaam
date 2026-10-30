import time, uuid
import pytest
from sqlalchemy import select
from backend.tests.test_core import system
from backend.tests.test_global_integrations import rental_setup
from backend.tests.test_city_platform import setup_bus
from backend.api.economy import balance, credit
from backend.api.models import Ledger, Presence, User
from backend.api.mobility import RentalLease

@pytest.mark.parametrize('kind', ['bike', 'ebike', 'car'])
def test_xp_rental_balance_quote_retry_and_insufficient(system, kind):
    c, sessions = system
    h, user, _ = rental_setup(c, sessions, kind)
    asset = next(a for a in c.get('/api/mobility', headers=h).json()['assets'] if a['id']=='asset_'+kind)
    assert asset['currency']=='xp'
    url='/api/mobility/assets/asset_'+kind+'/rent'
    request={'id':str(uuid.uuid4()), 'expected_cost':asset['cost'], 'expected_currency':'xp'}
    with sessions.begin() as db:
        credit(db,user['id'],-balance(db,user['id'],'xp'),'test_spend','fixture','empty',currency='xp')
    before=c.get('/api/wallet',headers=h).json()
    denied=c.post(url,headers=h,json=request)
    assert denied.status_code==409 and denied.json()['detail']['code']=='INSUFFICIENT_XP'
    assert denied.json()['detail']['shortfall']==asset['cost']
    assert c.get('/api/wallet',headers=h).json()==before
    with sessions.begin() as db:
        assert db.get(RentalLease,request['id']) is None
        credit(db,user['id'],asset['cost'],'test_earn','fixture','fund',currency='xp')
    stale=c.post(url,headers=h,json={**request,'expected_currency':'credits'})
    assert stale.status_code==409 and stale.json()['detail']['code']=='CURRENCY_CHANGED'
    first=c.post(url,headers=h,json=request)
    assert first.status_code==200,first.text
    assert c.post(url,headers=h,json=request).status_code==200
    assert c.post(url,headers=h,json={**request,'id':str(uuid.uuid4())}).status_code==409
    after=c.get('/api/wallet',headers=h).json()
    assert after['xp']==0 and after['credits']==before['credits']
    with sessions() as db:
        rows=list(db.scalars(select(Ledger).where(Ledger.user_id==user['id'],Ledger.kind.in_(['car_rental_xp','bike_rental_xp']))))
        assert len(rows)==1 and rows[0].currency=='xp' and rows[0].amount==-asset['cost']
        assert db.get(RentalLease,request['id']).settings['currency']=='xp'

def test_bus_xp_new_request_id_refresh_retry_and_old_quote(system,monkeypatch):
    c,sessions=system
    a,b,vehicle,start=setup_bus(c,sessions,monkeypatch)
    h,user=a
    c.post('/api/transit/hail',headers=h,json={'vehicle_id':vehicle})
    request={'id':str(uuid.uuid4()),'vehicle_id':vehicle,'expected_fare':20,'expected_currency':'xp'}
    before=c.get('/api/wallet',headers=h).json()
    denied=c.post('/api/transit/board',headers=h,json={**request,'expected_currency':'credits'})
    assert denied.status_code==409 and denied.json()['detail']['code']=='CURRENCY_CHANGED'
    assert c.post('/api/transit/board',headers=h,json=request).status_code==200
    assert c.get('/api/transit/board/london',headers=h).json()['journey']['ticket_id']==request['id']
    assert c.post('/api/transit/board',headers=h,json={**request,'id':str(uuid.uuid4())}).json()['duplicate']
    after=c.get('/api/wallet',headers=h).json()
    assert after['xp']==before['xp']-20 and after['credits']==before['credits']

def test_historical_credit_rental_retry_is_unchanged(system):
    c,sessions=system
    h,user,_=rental_setup(c,sessions,'bike')
    rental_id=str(uuid.uuid4())
    old_settings={'name':'City Bike','price':10,'minutes':10,'speed':18,'acceleration':5,'brake':12}
    with sessions.begin() as db:
        credit(db,user['id'],-10,'vehicle_rental','asset_bike','rental:'+rental_id)
        db.add(RentalLease(id=rental_id,user_id=user['id'],asset_id='asset_bike',price=10,settings=old_settings,
                           expires_at=time.time()-10,ended_at=time.time()-10,return_x=0,return_z=0))
    before=c.get('/api/wallet',headers=h).json()
    result=c.post('/api/mobility/assets/asset_bike/rent',headers=h,json={'id':rental_id,'expected_cost':10})
    assert result.status_code==200
    assert result.json()['rental']['settings']==old_settings
    assert c.get('/api/wallet',headers=h).json()==before

def test_scooter_still_charges_credits(system):
    c,sessions=system
    h,user,_=rental_setup(c,sessions,'scooter')
    before=c.get('/api/wallet',headers=h).json()
    response=c.post('/api/mobility/assets/asset_scooter/rent',headers=h,json={
        'id':str(uuid.uuid4()),'expected_cost':20,'expected_currency':'credits'})
    assert response.status_code==200,response.text
    after=c.get('/api/wallet',headers=h).json()
    assert before['credits']-after['credits']==20 and before['xp']==after['xp']

def test_other_activity_admin_limits_are_preserved(system):
    from backend.api.mobility import DEFAULTS
    c,sessions=system
    h,user,_=rental_setup(c,sessions,'bike')
    with sessions.begin() as db:
        db.get(User,user['id']).role='super_admin'
    for kind in ['scooter','boat','swim']:
        for override in [{'speed':46},{'acceleration':21}]:
            response=c.put('/api/super-admin/vehicles/types/'+kind,headers=h,json={**DEFAULTS[kind],**override})
            assert response.status_code==422

def test_indoor_speed_unchanged_outdoor_uses_controlled_pace(system,monkeypatch):
    from backend.api import world
    c,sessions=system
    h,user,_=rental_setup(c,sessions,'bike')
    clock=[time.time()]
    monkeypatch.setattr(world.time,'time',lambda:clock[0])
    with sessions.begin() as db:
        p=db.get(Presence,user['id']);u=db.get(User,user['id'])
        for mode,base in [('walk',world.WALK_SPEED),('run',world.RUN_SPEED)]:
            distances={}
            for zone in ['world','building:test-indoor']:
                p.x=p.z=0;p.zone_id=zone;p.motion_speed=base*(3 if zone=='world' else 1);p.last_move=clock[0]
                clock[0]+=.12
                world.move(world.Movement(dx=1,dz=0,mode=mode),u,db)
                distances[zone]=p.x
            assert distances['world']==pytest.approx(distances['building:test-indoor']*(.16 if mode=='walk' else .2))
