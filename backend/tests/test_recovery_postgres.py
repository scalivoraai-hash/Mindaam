"""Independent PostgreSQL transactions for the new recovery and occupancy paths."""
import os,time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import pytest
from sqlalchemy import select,text,func
from sqlalchemy.orm import sessionmaker
from backend.api import main,operator_recovery
from backend.api.db import Base,engine,APP_ENV
from backend.api.models import User,Presence,Event,Attendee,Ledger,Audit
from backend.api.auditorium_seating import Seat,synchronize,CHAIRS
from backend.api.commerce import Payment
from backend.api.economy import balance

@pytest.fixture
def postgres():
    if not os.getenv('DATABASE_URL','').startswith('postgresql'):pytest.skip('Requires existing PostgreSQL CI service')
    assert APP_ENV=='test'
    schema='release_recovery_'+uuid4().hex
    scoped=engine.execution_options(schema_translate_map={None:schema})
    with engine.begin() as db:db.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        Base.metadata.create_all(scoped)
        sessions=sessionmaker(scoped,expire_on_commit=False)
        with sessions.begin() as db:
            for name in ['admin','alice','bob']:
                db.add(User(id=name,username=name,email=name+'@example.test',password_hash='not-a-login',role='super_admin' if name=='admin' else 'user'))
        yield sessions
    finally:
        with engine.begin() as db:db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))

def test_postgres_two_verified_reconciliations_credit_once(postgres,monkeypatch):
    sessions=postgres;barrier=Barrier(2)
    with sessions.begin() as db:
        db.add(Payment(id='purchase',user_id='alice',sku='credits',credits=500,amount_pence=500,provider_id='cs_purchase',request_key='local-purchase'))
    receipt={'id':'cs_purchase','livemode':False,'mode':'payment','status':'complete','payment_status':'paid',
        'amount_total':500,'currency':'gbp','metadata':{'payment_id':'purchase'},
        'payment_intent':{'id':'pi_purchase','status':'succeeded','amount_received':500,'currency':'gbp','livemode':False,
            'latest_charge':{'id':'ch_purchase','paid':True,'captured':True,'amount':500,'currency':'gbp',
                'payment_intent':'pi_purchase','livemode':False,'amount_refunded':0,'refunded':False,'disputed':False}}}
    def provider(_):barrier.wait(timeout=5);return receipt
    monkeypatch.setattr(operator_recovery,'provider_checkout',provider)
    def recover(_):
        with sessions() as db:
            result=operator_recovery.reconcile('alice','purchase',operator_recovery.Reconcile(confirmed=True,reason='Concurrent local recovery regression'),db.get(User,'admin'),db)
            db.commit();return result
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(recover,range(2)))
    assert sum(r['already_recorded'] for r in results)==1
    with sessions() as db:
        assert balance(db,'alice')==500 and balance(db,'alice','xp')==0
        assert db.scalar(select(func.count()).select_from(Ledger).where(Ledger.kind=='purchase'))==1
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action=='payment.reconciled'))==1

def test_postgres_one_chair_has_one_occupant(postgres):
    sessions=postgres;barrier=Barrier(2)
    with sessions.begin() as db:
        db.add(Event(id='venue',host_id='admin',city='london',title='Local occupancy race',starts_at=time.time(),status='live',venue_mode='virtual_auditorium',venue_experience_type='auditorium'));db.flush()
        for name in ['alice','bob']:
            db.add(Attendee(event_id='venue',user_id=name,state='active',role='audience'))
            db.add(Presence(user_id=name,city='london',zone_id='event:venue',x=CHAIRS[0][0],z=CHAIRS[0][1],last_move=time.time()-2,updated_at=time.time()))
    def sit(name):
        with sessions.begin() as db:
            u=db.scalar(select(User).where(User.id==name).with_for_update())
            p=db.scalar(select(Presence).where(Presence.user_id==name).with_for_update())
            barrier.wait(timeout=5)
            return synchronize(db,p,u,{'template':'auditorium','id':'venue'})
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(sit,['alice','bob']))
    with sessions() as db:
        rows=list(db.execute(select(Seat.user_id,Seat.number)))
        attendees=list(db.execute(select(Attendee.user_id,Attendee.state,Presence.zone_id,Presence.updated_at).join(Presence,Presence.user_id==Attendee.user_id)))
        assert results.count(0)==1 and results.count(None)==1,(results,rows,attendees,time.time())
        assert len(rows)==1
