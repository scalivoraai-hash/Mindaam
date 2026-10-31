"""Disposable local data only: beta blocks new charges without touching ledgers."""
import time, uuid
import pytest
from sqlalchemy import select, func
from backend.tests.test_core import system, register, onboard
from backend.api.models import Ledger
from backend.api.commerce import Payment
from backend.api.payment_policy import actions_enabled, MESSAGE
from backend.api.payment_settlement import configured

@pytest.mark.parametrize('flag',[None,'false','','TRUE','1'])
def test_production_switch_fails_closed(monkeypatch,flag):
 monkeypatch.setenv('APP_ENV','production')
 if flag is None:monkeypatch.delenv('MINDAAM_PAYMENT_ACTIONS_ENABLED',raising=False)
 else:monkeypatch.setenv('MINDAAM_PAYMENT_ACTIONS_ENABLED',flag)
 assert actions_enabled() is False

def test_production_never_offers_sandbox_checkout(monkeypatch):
 monkeypatch.setenv('APP_ENV','production');monkeypatch.setenv('MINDAAM_PAYMENT_ACTIONS_ENABLED','true')
 monkeypatch.setenv('STRIPE_SECRET_KEY','sk_test_disposable');monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','not-a-real-secret')
 assert not configured()
 monkeypatch.setenv('STRIPE_SECRET_KEY','sk_live_disposable');assert configured()

def test_beta_blocks_all_new_payment_paths_preserves_free_and_wallet(system,monkeypatch):
 c,dbs=system;h,u=register(c,'beta_host');onboard(c,h);g,guest=register(c,'beta_guest');onboard(c,g)
 for auth in (h,g):assert c.get('/api/world/london',headers=auth).status_code==200
 monkeypatch.setenv('MINDAAM_PAYMENT_ACTIONS_ENABLED','false')
 before=c.get('/api/wallet',headers=h).json()
 with dbs() as db:payments=db.scalar(select(func.count()).select_from(Payment));ledger=db.scalar(select(func.count()).select_from(Ledger))
 for mode in ('standard','virtual_auditorium'):
  e=c.post('/api/events',headers=h,json={'title':'Free beta event','city':'london','starts_at':time.time(),'venue_mode':mode}).json();url='/api/events/'+e['id']
  assert c.post(url+'/state/start',headers=h).status_code==200
  assert c.post(url+'/join',headers=g).status_code==200
  if mode=='virtual_auditorium':
   for suffix in ('enter','exit','enter'):assert c.post(url+'/venue/'+suffix,headers=g).status_code==200
  assert c.post(url+'/state/cancel',headers=h).status_code==200
  for route,data in [(url+'/venue/booking',{'request_id':str(uuid.uuid4()),'hours':1,'expected_cost':100}), (url+'/tickets',{'request_id':str(uuid.uuid4()),'expected_cost':25})]:
   r=c.post(route,headers=h,json=data);assert r.status_code==409,r.text;assert r.json()["detail"]==MESSAGE
 for route,data in [('/api/payments/checkout',{'sku':'credits_starter','request_id':str(uuid.uuid4()),'expected_amount':199}),('/api/subscriptions/checkout',{'plan_id':'test','request_id':str(uuid.uuid4())}),('/api/subscriptions/test/portal',{})]:
  r=c.post(route,headers=h,json=data);assert r.status_code==409,r.text;assert r.json()["detail"]==MESSAGE
 assert c.get('/api/wallet',headers=h).json()==before
 packs=c.get('/api/payments/credits',headers=h).json();assert packs['packs'] and packs['ready'] is False
 assert c.get('/api/config').json()['flags']['payment_actions_enabled'] is False
 assert c.get('/api/venue-rentals/london',headers=h).json()['enabled'] is False
 assert c.get('/api/super-admin/overview',headers=h).status_code==403
 assert c.get('/api/super-admin/overview').status_code==401
 with dbs() as db:
  assert db.scalar(select(func.count()).select_from(Payment))==payments
  assert db.scalar(select(func.count()).select_from(Ledger))==ledger
 # Closed payment switch must not disable signed reconciliation endpoints.
 for route in ('/api/payments/webhook','/api/subscriptions/webhook'):
  r=c.post(route,content='{}');assert 'temporarily unavailable during public beta' not in r.text
