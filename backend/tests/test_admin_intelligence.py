"""Data accuracy and dialect regression tests for operator-only read models."""
import os,time,uuid
import pytest
from sqlalchemy import select,func
from backend.tests.test_core import system,register
from backend.tests.test_operator_control import operator
from backend.api.models import User,Event,Ledger,Audit
from backend.api.commerce import Payment,PaymentEvent
from backend.api.operations import UserActivity
from backend.api.economy import credit


def test_overview_period_finance_and_events_are_separate(system):
 c,dbs=system;admin,owner=operator(c,dbs);now=time.time();day=int(now/86400)
 with dbs.begin() as db:
  db.add_all([Event(id='ended',host_id=owner['id'],title='Ended event',city='london',starts_at=now-3600,status='ended'),Event(id='live',host_id=owner['id'],title='Live event',city='london',starts_at=now-60,status='live',venue_mode='virtual_auditorium')])
  db.add_all([Payment(id='p',user_id=owner['id'],sku='starter',amount_pence=199,credits=200,status='paid',provider_id='checkout_unique',request_key='p',created_at=now-100),Payment(id='pending',user_id=owner['id'],sku='starter',amount_pence=999,credits=200,status='pending',request_key='pending',created_at=now-100)])
  db.add_all([PaymentEvent(id='delivery1',event_type='checkout.session.completed'),PaymentEvent(id='delivery2',event_type='payment_intent.succeeded')])
  db.add(UserActivity(user_id=owner['id'],day=day,last_seen=now))
  credit(db,owner['id'],500,'purchase','p','test-purchase')
  credit(db,owner['id'],20,'collectible','fruit','test-xp','xp')
 r=c.get('/api/super-admin/overview?days=7',headers=admin);assert r.status_code==200,r.text
 data=r.json();k=data['kpis']
 assert k['registered_users']==1 and k['total_events']==2 and k['live_events']==1 and k['completed_events']==1
 assert k['gross_payments_pence']==199 and k['completed_purchases']==1
 assert k['credits_purchased']==500 and k['xp_awarded']==20 and k['credits_earned']==0
 assert sum(x['gross_pence'] for x in data['payment_trend'])==199
 assert data['active_trend'][-1]['daily']==1
 assert len(data['registrations'])==1 and data['registrations'][0]['count']==1
 assert c.get('/api/super-admin/overview?start=nan',headers=admin).status_code==422
 assert c.get('/api/super-admin/overview?start=0',headers=admin).status_code==422
 assert c.get(f'/api/super-admin/overview?start={now+100}&end={now}',headers=admin).status_code==422
 old=c.get(f'/api/super-admin/overview?start={now-86400*40}&end={now-86400*39}',headers=admin).json()
 assert old['registrations']==[] and old['payment_trend']==[]
 assert old['kpis']['gross_payments_pence']==0


def test_records_real_pagination_filter_detail_and_roles(system):
 c,dbs=system;ordinary,person=register(c,'normal');admin,owner=operator(c,dbs)
 with dbs.begin() as db:
  db.add_all([Event(id=f'event-{i:03}',host_id=person['id'],title=f'Conference {i:03}',city='london',starts_at=time.time(),status='scheduled',created_at=100+i) for i in range(31)])
 for tab in ['profile','activity','reports']:
  response=c.get(f'/api/super-admin/users/{person["id"]}/detail?tab={tab}',headers=admin)
  assert response.status_code==200,response.text
 before=c.get('/api/super-admin/records/audit',headers=admin).json()['total']
 path='/api/super-admin/records/events'
 for url in [path,path+'/event-000','/api/super-admin/events/event-000/participants']:
  assert c.get(url,headers=ordinary).status_code==403
 page1=c.get(path+'?limit=10&sort=oldest',headers=admin).json();page2=c.get(path+'?limit=10&page=2&sort=oldest',headers=admin).json()
 assert page1['total']==31 and len(page1['items'])==10 and len(page2['items'])==10
 assert not {r['id'] for r in page1['items']} & {r['id'] for r in page2['items']}
 assert page1['items'][0]['username']=='normal' and page1['items'][0]['venue_mode']=='standard'
 assert c.get(path+'?q=Conference%20007',headers=admin).json()['total']==1
 assert c.get(path+'?status=live',headers=admin).json()['total']==0
 for suffix in ['?page=0','?limit=101','?sort=password_hash','?days=999']:
  assert c.get(path+suffix,headers=admin).status_code==422
 detail=c.get(path+'/event-000',headers=admin).json()
 assert detail['user']['username']=='normal' and detail['record']['title']=='Conference 000'
 assert not any(key in str(detail) for key in ['password_hash','latitude','longitude'])
 for kind in ['payments','businesses','enquiries','campaigns','reservations','tickets','subscriptions','reports','audit','transactions','xp','rentals','transport','stops','buildings','missions','claims','city_requests','assets']:
  response=c.get('/api/super-admin/records/'+kind+'?limit=10',headers=admin)
  assert response.status_code==200,(kind,response.text)
  assert len(response.json()['items'])<=10
 assert c.get('/api/super-admin/records/unknown',headers=admin).status_code==404
 assert c.get('/api/super-admin/records/audit',headers=admin).json()['total']==before


@pytest.mark.skipif(not os.getenv('DATABASE_URL','').startswith('postgresql'),reason='Real PostgreSQL service supplied by the backend CI job')
def test_postgresql_overview_grouping_regression():
 from sqlalchemy.orm import Session
 from sqlalchemy.exc import ProgrammingError
 from backend.api.db import engine
 from backend.api.operations import overview,finance
 # Run against migrated CI schema and roll back: no resets or fixture users.
 with engine.connect() as conn:
  transaction=conn.begin();db=Session(bind=conn)
  try:
   with pytest.raises(ProgrammingError):
    with conn.begin_nested():
     conn.execute(select(func.floor(User.created_at/86400)*86400,func.count()).group_by(func.floor(User.created_at/86400)))
   result=overview(days=7,start=None,end=None,u=None,db=db)
   assert 'registered_users' in result['kpis']
   result=finance(days=7,u=None,db=db)
   assert result['currency']=='GBP'
  finally:
   db.close();transaction.rollback()


def test_reservation_receipt_reconciles_immutable_ledger(system):
 from backend.api.venue_rentals import VenueBooking
 c,dbs=system;admin,owner=operator(c,dbs)
 with dbs.begin() as db:
  event=Event(id='receipt-event',host_id=owner['id'],title='Receipt',city='london',starts_at=time.time(),status='cancelled',venue_mode='grand_arena');db.add(event);db.flush()
  credit(db,owner['id'],100,'purchase','local-receipt','local-receipt')
  debit=credit(db,owner['id'],-100,'venue_rental','receipt-booking','local-booking')
  db.add(VenueBooking(id='receipt-booking',request_id='local',user_id=owner['id'],event_id=event.id,city='london',starts_at=time.time(),ends_at=time.time()+3600,hours=1,cost=100,ledger_id=debit.id))
  credit(db,owner['id'],100,'venue_refund','receipt-booking','local-refund')
 response=c.get('/api/super-admin/records/reservations/receipt-booking',headers=admin)
 assert response.status_code==200,response.text
 data=response.json();assert data['record']['event_status']=='cancelled' and data['record']['refunded'] is True
 assert data['record']['cost']==100 and data['ledger'][0]['amount']==-100
 listing=c.get('/api/super-admin/records/reservations',headers=admin).json()
 assert listing['items'][0]['event_status']=='cancelled'
