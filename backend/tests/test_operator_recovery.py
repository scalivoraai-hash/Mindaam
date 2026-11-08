"""Local provider fixtures prove failure-closed reconciliation, not live Stripe acceptance."""
import copy
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,func
from backend.tests.test_core import system,register,onboard
from backend.tests.test_operator_control import operator
from backend.api import operator_recovery
from backend.api.models import User,Ledger,Audit
from backend.api.commerce import Payment
from backend.api.economy import balance

def setup(system,monkeypatch):
    c,sessions=system
    admin,owner=operator(c,sessions)
    auth,person=register(c,'recoverable');onboard(c,auth)
    with sessions.begin() as db:
        db.add(Payment(id='existing-purchase',user_id=person['id'],sku='credits_500',amount_pence=500,credits=500,provider_id='cs_existing',request_key='existing-checkout'))
    receipt={'id':'cs_existing','livemode':False,'mode':'payment','status':'complete','payment_status':'paid',
        'amount_total':500,'currency':'gbp','metadata':{'payment_id':'existing-purchase'},
        'payment_intent':{'id':'pi_existing','status':'succeeded','amount_received':500,'currency':'gbp','livemode':False,
            'latest_charge':{'id':'ch_existing','paid':True,'captured':True,'amount':500,'currency':'gbp',
                'payment_intent':'pi_existing','livemode':False,'amount_refunded':0,'refunded':False,'disputed':False}}}
    monkeypatch.setattr(operator_recovery,'provider_checkout',lambda provider_id:copy.deepcopy(receipt))
    path=f'/api/super-admin/users/{person["id"]}/payments/existing-purchase/reconcile'
    body={'confirmed':True,'reason':'Recover missing verified purchase webhook'}
    return c,sessions,admin,auth,person,receipt,path,body

def test_verified_payment_concurrent_and_repeated_reconciliation_exactly_once(system,monkeypatch):
    c,sessions,admin,auth,person,receipt,path,body=setup(system,monkeypatch)
    assert c.post(path,headers=auth,json=body).status_code==403
    with ThreadPoolExecutor(max_workers=2) as workers:
        results=list(workers.map(lambda _:c.post(path,headers=admin,json=body),range(2)))
    assert all(r.status_code==200 for r in results),[r.text for r in results]
    assert sum(r.json()['already_recorded'] for r in results)==1
    assert c.post(path,headers=admin,json=body).json()['already_recorded']
    with sessions() as db:
        assert balance(db,person['id'])==500 and balance(db,person['id'],'xp')==20
        assert db.scalar(select(func.count()).select_from(Ledger).where(Ledger.kind=='purchase'))==1
        audit=db.scalar(select(Audit).where(Audit.action=='payment.reconciled'))
        assert audit.details['proof']['session_id']=='cs_existing'
        assert audit.details['before']==0 and audit.details['after']==500
        assert db.get(Payment,'existing-purchase').status=='paid'

@pytest.mark.parametrize('change',['unpaid','amount','currency','metadata','intent','uncaptured','refund','dispute','live','local_refund','local_dispute','suspended','extra_amount'])
def test_unverified_purchase_cannot_mint_pc(system,monkeypatch,change):
    c,sessions,admin,auth,person,receipt,path,body=setup(system,monkeypatch)
    charge=receipt['payment_intent']['latest_charge']
    if change=='unpaid':receipt['payment_status']='unpaid'
    elif change=='amount':receipt['amount_total']=1
    elif change=='currency':receipt['currency']='usd'
    elif change=='metadata':receipt['metadata']['payment_id']='another-purchase'
    elif change=='intent':receipt['payment_intent']['amount_received']=1
    elif change=='uncaptured':charge['captured']=False
    elif change=='refund':charge['amount_refunded']=1
    elif change=='dispute':charge['disputed']=True
    elif change=='live':receipt['livemode']=True
    elif change=='extra_amount':body['amount']=5000
    else:
        with sessions.begin() as db:
            if change=='suspended':db.get(User,person['id']).suspended=True
            elif change=='local_refund':db.get(Payment,'existing-purchase').refunded_pence=1
            else:db.get(Payment,'existing-purchase').dispute_status='needs_response'
    assert c.post(path,headers=admin,json=body).status_code in (409,422)
    with sessions() as db:
        assert balance(db,person['id'])==0
        assert not db.scalar(select(Ledger.id).where(Ledger.kind=='purchase'))
        assert not db.scalar(select(Audit.id).where(Audit.action=='payment.reconciled'))

def test_profile_correction_preserves_preferences_and_requires_fresh_review(system):
    c,sessions=system;admin,owner=operator(c,sessions);auth,person=register(c,'profilemember')
    with sessions.begin() as db:db.get(User,person['id']).profile={'display_name':'Before','show_location':False,'links':{'website':{'url':'https://example.com','visible':False}}}
    path=f'/api/super-admin/users/{person["id"]}/profile'
    body={'expected':{'display_name':'Before'},'profile':{'display_name':'Corrected name'},'reason':'User requested spelling correction'}
    assert c.patch(path,headers=auth,json=body).status_code==403
    assert c.patch(path,headers=admin,json={**body,'profile':{'username':'changed'}}).status_code==422
    assert c.patch(path,headers=admin,json=body).status_code==200
    assert c.patch(path,headers=admin,json=body).status_code==409
    assert c.get('/api/me',headers=auth).json()['profile']['display_name']=='Corrected name'
    with sessions() as db:
        user=db.get(User,person['id']);assert user.profile['show_location'] is False
        assert user.profile['links']['website']['visible'] is False
        assert db.scalar(select(Audit).where(Audit.action=='user.profile_corrected')).details['before']=={'display_name':'Before'}

def test_user_property_and_overview_read_models(system):
    from backend.api.property_economy import Property
    c,sessions=system;admin,owner=operator(c,sessions);auth,person=register(c);onboard(c,auth)
    with sessions.begin() as db:
        db.add(Property(id='local-test-property',city='london',category='house',title='Local test',x=0,z=0,owner=person['id'],name='Named home',cost=2000,acquired=100))
    root=f'/api/super-admin/users/{person["id"]}/detail'
    assert c.get(root+'?tab=properties',headers=auth).status_code==403
    properties=c.get(root+'?tab=properties',headers=admin).json()
    assert properties['total']==1 and properties['items'][0]['name']=='Named home'
    kpis=c.get(root,headers=admin).json()['kpis']
    assert kpis['Owned properties']==1 and kpis['Spendable XP']==20 and kpis['Pulse Credits']==0
