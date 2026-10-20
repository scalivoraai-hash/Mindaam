"""Shared production regressions. All users, tickets and funds are local fixtures."""
import time, uuid
from backend.tests.test_core import system
from backend.tests.test_city_platform import setup_bus
from backend.tests.test_talk import pair
from backend.api import main
from backend.api.models import Presence
from backend.api.mobility import RentalAsset, RentalLease, DEFAULTS


def test_remote_rental_has_authoritative_identity_heading_and_exit(system):
    c, sessions, a, ua, b, ub = pair(system)
    with sessions.begin() as db:
        p = db.get(Presence, ua['id'])
        db.add(RentalAsset(id='local-test-car', city=p.city, kind='car', x=p.x, z=p.z, active_user_id=ua['id']))
        db.flush()
        db.add(RentalLease(id=str(uuid.uuid4()), user_id=ua['id'], asset_id='local-test-car', price=0,
            settings=DEFAULTS['car'], expires_at=time.time()+600, return_x=p.x, return_z=p.z, heading=1.2, speed=8))
        p.mode='car'
    peer = next(p for p in c.get('/api/world/london', headers=b).json()['players'] if p['id']==ua['id'])
    assert peer['vehicle']['id']=='local-test-car'
    assert peer['vehicle']['kind']=='car' and peer['vehicle']['heading']==1.2
    assert peer['movement_state']=='IN_CAR'
    assert c.post('/api/mobility/exit', headers=a).status_code==200
    peer = next(p for p in c.get('/api/world/london', headers=b).json()['players'] if p['id']==ua['id'])
    assert peer['vehicle'] is None and peer['mode']=='walk'


def test_bus_boarding_advances_motion_revision_and_projects_passenger(system, monkeypatch):
    c, sessions=system
    a,b,vehicle,start=setup_bus(c,sessions,monkeypatch)
    with sessions.begin() as db: db.get(Presence,a[1]['id']).last_move=start+4
    assert c.post('/api/transit/hail',headers=a[0],json={'vehicle_id':vehicle}).status_code==200
    response=c.post('/api/transit/board',headers=a[0],json={'id':str(uuid.uuid4()),'vehicle_id':vehicle,'expected_currency':'xp','expected_fare':20})
    assert response.status_code==200
    position=response.json()['position']
    assert position['last_move']>start+4 and position['zone_id']=='bus:'+vehicle
    peer=next(p for p in c.get('/api/world/london',headers=b[0]).json()['players'] if p['id']==a[1]['id'])
    assert peer['movement_state']=='ON_BUS' and peer['vehicle']['id']==vehicle
    assert peer['seated'] and peer['vehicle']['seat']==response.json()['journey']['seat']


def test_connection_interrupt_preserves_position_but_hides_stale_presence(system):
    c,sessions,a,ua,b,ub=pair(system)
    with sessions.begin() as db:
        p=db.get(Presence,ua['id']);before=(p.x,p.z,p.city,p.zone_id);p.updated_at=time.time()-65
    main.maintenance()
    with sessions() as db:
        p=db.get(Presence,ua['id'])
        assert p is not None and (p.x,p.z,p.city,p.zone_id)==before
    assert not any(p['id']==ua['id'] for p in c.get('/api/world/london',headers=b).json()['players'])
    resumed=c.get('/api/world/london',headers=a).json()['position']
    assert (resumed['x'],resumed['z'])==before[:2]
