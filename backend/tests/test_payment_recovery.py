"""Signed local Stripe fixtures exercise ledger invariants; not provider acceptance."""
import pytest
from sqlalchemy import select,func
from fastapi import HTTPException
from backend.api.main import app  # Register all existing model tables before the fixture creates its database.
from backend.tests.test_commerce import commerce,signed
from backend.api.commerce import Payment
from backend.api.models import Ledger
from backend.api.economy import credit,balance
from backend.api.payment_settlement import summary

SECRET='whsec_local_recovery_fixture'
def prepare(commerce,monkeypatch):
 client,sessions=commerce;monkeypatch.setenv('STRIPE_WEBHOOK_SECRET',SECRET)
 with sessions.begin() as db:
  db.add(Payment(id='recovery-payment',user_id='player',sku='credits_500',amount_pence=500,credits=500,provider_id='cs_recovery',request_key='recovery-request'))
 return client,sessions

def completed(id='paid'):
 return {'id':id,'object':'event','type':'checkout.session.completed','livemode':False,'data':{'object':{'id':'cs_recovery','object':'checkout.session','payment_intent':'pi_recovery','metadata':{'payment_id':'recovery-payment'},'payment_status':'paid','amount_total':500,'currency':'gbp'}}}
def refund(amount,id='refund'):
 return {'id':id,'object':'event','type':'charge.refunded','livemode':False,'data':{'object':{'id':'ch_recovery','object':'charge','payment_intent':'pi_recovery','metadata':{'payment_id':'recovery-payment'},'amount':500,'amount_refunded':amount,'currency':'gbp'}}}
def dispute(status,created,id):
 return {'id':id,'object':'event','type':'charge.dispute.closed' if status in ('won','lost') else 'charge.dispute.created','created':created,'livemode':False,'data':{'object':{'id':'dp_recovery','object':'dispute','payment_intent':'pi_recovery','status':status,'amount':500,'currency':'gbp'}}}
def send(client,event):
 r=signed(client,event,SECRET);assert r.status_code==200,r.text;return r.json()

def test_refund_before_completion_and_duplicate_partial_delivery(commerce,monkeypatch):
 client,sessions=prepare(commerce,monkeypatch)
 send(client,refund(200));send(client,completed());send(client,refund(100,'older-refund'));send(client,completed('duplicate-paid'))
 assert send(client,refund(200))['duplicate']
 with sessions() as db:
  assert balance(db,'player')==300
  assert db.get(Payment,'recovery-payment').reversed_credits==200
  assert db.scalar(select(func.count()).select_from(Ledger).where(Ledger.kind=='purchase'))==1
  assert not summary(db,'player')['spending_paused']

def test_refund_spent_balance_recovery_never_negative(commerce,monkeypatch):
 client,sessions=prepare(commerce,monkeypatch);send(client,completed())
 with sessions.begin() as db:credit(db,'player',-450,'event_ticket','local-ticket','spend')
 send(client,refund(500))
 with sessions() as db:
  assert balance(db,'player')==0;assert summary(db,'player')['pending_recovery']==450
  with pytest.raises(HTTPException) as error:credit(db,'player',-1,'vehicle','local-car','blocked')
  assert error.value.status_code==409
 with sessions.begin() as db:
  credit(db,'player',500,'purchase','second-local-payment','replenish')
  assert balance(db,'player')==50;assert not summary(db,'player')['spending_paused']
  rows=list(db.scalars(select(Ledger).order_by(Ledger.created_at)))
  running=0
  for row in rows:
   assert row.previous_balance==running;running+=row.amount;assert row.balance==running;assert running>=0

@pytest.mark.parametrize('outcome',['won','lost'])
def test_dispute_blocks_spending_and_terminal_state_ignores_stale_events(commerce,monkeypatch,outcome):
 client,sessions=prepare(commerce,monkeypatch);send(client,completed());send(client,dispute('needs_response',100,'open'))
 with sessions() as db:
  assert summary(db,'player')['disputed']
  with pytest.raises(HTTPException):credit(db,'player',-1,'event_ticket','local','block')
 send(client,dispute(outcome,200,'close'));send(client,dispute('under_review',100,'late-open'))
 with sessions() as db:
  assert not summary(db,'player')['spending_paused'];assert balance(db,'player')==(500 if outcome=='won' else 0)
  assert db.get(Payment,'recovery-payment').dispute_status==outcome

def test_sandbox_rejects_live_key_and_live_event(commerce,monkeypatch):
 from backend.api.payment_settlement import configured
 client,sessions=prepare(commerce,monkeypatch)
 monkeypatch.setenv('APP_ENV','staging');monkeypatch.setenv('STRIPE_SECRET_KEY','sk_live_not_a_real_key')
 assert not configured()
 from backend.api.subscriptions import secret as subscription_key
 with pytest.raises(HTTPException):subscription_key()
 e=completed();e['livemode']=True;assert signed(client,e,SECRET).status_code==400
 monkeypatch.setenv('STRIPE_SECRET_KEY','rk_test_not_a_real_key');assert configured()

def test_mismatched_refund_rolls_back_event_and_wallet(commerce,monkeypatch):
 client,sessions=prepare(commerce,monkeypatch);send(client,completed())
 e=refund(501);assert signed(client,e,SECRET).status_code==400
 e=refund(100);e['data']['object']['currency']='usd';assert signed(client,e,SECRET).status_code==400
 with sessions() as db:assert balance(db,'player')==500

def test_checkout_server_price_concurrency_and_owner_status(commerce,monkeypatch):
 from concurrent.futures import ThreadPoolExecutor
 from types import SimpleNamespace
 import stripe
 client,sessions=prepare(commerce,monkeypatch)
 monkeypatch.setenv('STRIPE_SECRET_KEY','sk_test_local_fixture')
 calls=[]
 def provider(**kwargs):
  calls.append(kwargs);assert kwargs['line_items'][0]['price_data']['currency']=='gbp'
  assert kwargs['line_items'][0]['price_data']['unit_amount']==499
  assert kwargs['payment_intent_data']['metadata']['payment_id']==kwargs['metadata']['payment_id']
  return SimpleNamespace(id='cs_new',url='https://checkout.stripe.com/test-local-fixture')
 monkeypatch.setattr(stripe.checkout.Session,'create',provider)
 payload={'sku':'credits_500','request_id':'same-request-local','expected_amount':499}
 assert client.post('/api/payments/checkout',json={**payload,'expected_amount':1}).status_code==409
 with ThreadPoolExecutor(max_workers=2) as pool:
  results=list(pool.map(lambda _:client.post('/api/payments/checkout',json=payload),range(2)))
 assert all(r.status_code==200 for r in results);assert results[0].json()==results[1].json();assert len(calls)==1
 id=results[0].json()['payment_id'];assert client.get('/api/payments/'+id+'/status').json()['status']=='pending'
 assert client.get('/api/payments/'+id+'/status',headers={'x-user':'other'}).status_code==404
 with sessions() as db:assert balance(db,'player')==0
 e=completed('new-paid');obj=e['data']['object'];obj.update(id='cs_new',payment_intent='pi_new',amount_total=499,metadata={'payment_id':id});send(client,e)
 for typ in ['checkout.session.expired','checkout.session.async_payment_failed']:
  late=completed('late-'+typ);late['type']=typ;late['data']['object'].update(id='cs_new',payment_intent='pi_new',metadata={'payment_id':id});send(client,late)
 assert client.get('/api/payments/'+id+'/status').json()['status']=='paid'
 with sessions() as db:assert balance(db,'player')==500

@pytest.mark.parametrize('typ',['checkout.session.expired','checkout.session.async_payment_failed'])
def test_expired_or_declined_checkout_never_awards_credits(commerce,monkeypatch,typ):
 client,sessions=prepare(commerce,monkeypatch);e=completed('failure');e['type']=typ;e['data']['object']['payment_status']='unpaid';send(client,e)
 with sessions() as db:
  assert balance(db,'player')==0;assert db.get(Payment,'recovery-payment').status=='failed'
