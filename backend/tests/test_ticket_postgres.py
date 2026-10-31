"""Real PostgreSQL lock/conservation test in an isolated CI-only schema."""
import os,time
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from sqlalchemy import select,text,func
from sqlalchemy.orm import Session
from backend.api.models import User,Event,Ledger
from backend.api.event_tickets import purchase,Purchase,EventTicket,refund_cancelled
from backend.api.economy import credit,balance

@pytest.mark.skipif(not os.getenv('DATABASE_URL','').startswith('postgresql'),reason='Requires the existing backend CI PostgreSQL service')
def test_opposing_ticket_transfers_and_duplicate_requests_conserve_pc():
 from backend.api.db import Base,engine,APP_ENV
 from backend.api.expansion import seed_catalog
 from backend.api.growth import WorldAccess
 assert APP_ENV=='test'
 schema='ticket_conservation_'+uuid4().hex;scoped=engine.execution_options(schema_translate_map={None:schema})
 with engine.begin() as db:db.execute(text(f'CREATE SCHEMA "{schema}"'))
 try:
  Base.metadata.create_all(scoped)
  with Session(scoped) as db,db.begin():
   seed_catalog(db)
   for name in ['alpha','beta']:
    db.add(User(id=name,email=name+'@example.test',username=name,password_hash='not-a-login',onboarded=True))
   db.flush()
   for name in ['alpha','beta']:
    db.add(WorldAccess(user_id=name,destination_id='london',source='starter'))
    credit(db,name,100,'purchase','explicit-local-fixture','explicit-local-fixture')
    db.add(Event(id='event-'+name,host_id=name,title='Local conserved ticket',city='london',starts_at=time.time(),status='scheduled',ticket_price=20,capacity=20,venue_mode='standard'))
  barrier=Barrier(4);keys={name:uuid4() for name in ['alpha','beta']}
  def buy(name):
   with Session(scoped) as db,db.begin():
    db.execute(text("SET LOCAL lock_timeout='5s'"));u=db.get(User,name);barrier.wait(timeout=5)
    target='event-'+('beta' if name=='alpha' else 'alpha')
    return purchase(target,Purchase(request_id=keys[name],expected_cost=20),u,db)['id']
  with ThreadPoolExecutor(max_workers=4) as pool:
   futures=[pool.submit(buy,name) for name in ['alpha','alpha','beta','beta']]
   receipts=[f.result(timeout=15) for f in futures]
  assert receipts[0]==receipts[1] and receipts[2]==receipts[3] and receipts[0]!=receipts[2]
  with Session(scoped) as db,db.begin():
   assert balance(db,'alpha')==balance(db,'beta')==100
   assert db.scalar(select(func.count()).select_from(EventTicket))==2
   rows=list(db.scalars(select(Ledger).where(Ledger.kind.in_(['event_ticket','event_ticket_sale']))))
   assert len(rows)==4 and sum(r.amount for r in rows)==0
   for name in ['alpha','beta']:
    e=db.scalar(select(Event).where(Event.id=='event-'+name).with_for_update());refund_cancelled(db,e);e.status='cancelled'
   assert balance(db,'alpha')==balance(db,'beta')==100
   assert sum(db.scalars(select(Ledger.amount).where(Ledger.kind!='purchase')))==0
 finally:
  with engine.begin() as db:db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
