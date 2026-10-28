import uuid
from sqlalchemy import select,func
from backend.tests.test_core import system,register
from backend.api.models import User,Ledger,Audit
from backend.api.economy import balance

def operator(c,dbs):
 h,u=register(c,'operator')
 with dbs.begin() as db:db.get(User,u['id']).role='super_admin'
 return h,u

def test_directory_detail_permissions_and_private_fields(system):
 c,dbs=system;ordinary,user=register(c,'customer');admin,_=operator(c,dbs)
 for path in ['/directory','/finance','/records/audit','/users/'+user['id']+'/detail']:
  assert c.get('/api/super-admin'+path,headers=ordinary).status_code==403
 result=c.get('/api/super-admin/directory?q='+user['id'],headers=admin)
 assert result.status_code==200,result.text
 assert result.json()['total']==1
 row=result.json()['items'][0];assert row['id']==user['id'];assert 'password_hash' not in row
 for tab in ['overview','wallet','social','events','cities','payments','audit']:
  r=c.get('/api/super-admin/users/'+user['id']+'/detail?tab='+tab,headers=admin)
  assert r.status_code==200,r.text
  assert 'password_hash' not in r.text
 assert c.get('/api/super-admin/directory?page=0',headers=admin).status_code==422

def test_adjustment_idempotency_audit_and_limits(system):
 c,dbs=system;ordinary,user=register(c,'customer');admin,owner=operator(c,dbs)
 path='/api/super-admin/users/'+user['id']+'/adjustments'
 body={'request_id':str(uuid.uuid4()),'currency':'credits','amount':20,'purpose':'support','reason':'Documented support correction','confirmed':True}
 assert c.post(path,headers=ordinary,json=body).status_code==403
 with dbs() as db:before=balance(db,user['id'])
 first=c.post(path,headers=admin,json=body);assert first.status_code==200,first.text
 second=c.post(path,headers=admin,json=body);assert second.status_code==200 and second.json()['replayed']
 assert c.post(path,headers=admin,json={**body,'amount':21}).status_code==409
 assert c.post(path,headers=admin,json={**body,'request_id':str(uuid.uuid4()),'amount':1001}).status_code==409
 assert c.post(path,headers=admin,json={**body,'request_id':str(uuid.uuid4()),'amount':-999,'purpose':'correction'}).status_code==409
 assert c.post(path,headers=admin,json={**body,'confirmed':False}).status_code==422
 with dbs() as db:
  assert balance(db,user['id'])==before+20
  rows=list(db.scalars(select(Audit).where(Audit.action=='wallet.adjusted')));assert len(rows)==1
  assert rows[0].actor_id==owner['id'] and rows[0].details['reason']==body['reason']
  assert db.scalar(select(func.count()).select_from(Ledger).where(Ledger.kind=='admin_support'))==1

def test_status_requires_reason_and_records_operator(system):
 c,dbs=system;_,user=register(c,'customer');admin,owner=operator(c,dbs)
 path='/api/super-admin/users/'+user['id']+'/status'
 assert c.patch(path,headers=admin,json={'suspended':True,'reason':'x'}).status_code==422
 for value in [True,False]:
  r=c.patch(path,headers=admin,json={'suspended':value,'reason':'Documented moderation review'});assert r.status_code==200,r.text
 with dbs() as db:
  assert not db.get(User,user['id']).suspended
  assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action=='user.status_review'))==2

def test_independent_review_cannot_self_approve_or_duplicate(system):
 c,dbs=system;_,user=register(c,'customer');admin,owner=operator(c,dbs);reviewer,other=register(c,'reviewer')
 with dbs.begin() as db:db.get(User,other['id']).role='super_admin'
 body={'request_id':str(uuid.uuid4()),'currency':'credits','amount':2000,'purpose':'support','reason':'Documented exceptional support','confirmed':True}
 path='/api/super-admin/users/'+user['id']+'/adjustment-requests'
 with dbs() as db:before=balance(db,user['id'])
 r=c.post(path,headers=admin,json=body);assert r.status_code==200,r.text
 assert c.post(path,headers=admin,json=body).json()['id']==r.json()['id']
 decision='/api/super-admin/adjustment-requests/'+r.json()['id']+'/decision'
 payload={'approve':True,'confirmed':True,'reason':'Independent evidence review completed'}
 assert c.post(decision,headers=admin,json=payload).status_code==403
 with dbs() as db:assert balance(db,user['id'])==before
 for _ in range(2):
  r=c.post(decision,headers=reviewer,json=payload);assert r.status_code==200,r.text
 with dbs() as db:
  assert balance(db,user['id'])==before+2000
  from backend.api.venue_rentals import purchased_available
  assert purchased_available(db,user['id'])==0
  assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action=='wallet.review_approved'))==1

def test_finance_totals_include_records_beyond_display_limit(system):
 from backend.api.commerce import Payment
 c,dbs=system;_,user=register(c,'customer');admin,_=operator(c,dbs)
 with dbs.begin() as db:
  for i in range(1002):db.add(Payment(user_id=user['id'],sku='test_pack',amount_pence=100,credits=10,status='paid',refunded_pence=10,provider_id='test_'+str(i),request_key='qa_'+str(i)))
  db.add(Payment(user_id=user['id'],sku='test_pack',amount_pence=999,credits=10,status='pending',request_key='qa_pending'))
 r=c.get('/api/super-admin/finance',headers=admin);assert r.status_code==200,r.text
 d=r.json();assert d['gross_pence']==100200 and d['refund_pence']==10020 and d['successful_payments']==1002 and d['pending_payments']==1
 assert len(d['payments'])==1000

def test_operator_limits_and_password_gate(system):
 c,dbs=system;ordinary,_=register(c,'customer');admin,owner=operator(c,dbs)
 payload={'credits':100,'xp':1000,'daily_actions':5,'reason':'Documented operating policy','confirmed':True}
 assert c.put('/api/super-admin/adjustment-limits',headers=ordinary,json=payload).status_code==403
 assert c.put('/api/super-admin/adjustment-limits',headers=admin,json=payload).status_code==200
 assert c.put('/api/super-admin/adjustment-limits',headers=admin,json={**payload,'credits':10001}).status_code==422
 with dbs.begin() as db:db.get(User,owner['id']).must_change_password=True
 for path in ['directory','system-health','adjustment-limits','adjustment-requests']:
  assert c.get('/api/super-admin/'+path,headers=admin).status_code==403

def test_presence_counts_exclude_stale_and_suspended_and_separate_xp(system):
 import time
 from backend.api.models import Presence
 from backend.api.economy import credit
 c,dbs=system;_,user=register(c,'customer');_,stale=register(c,'stale');admin,_=operator(c,dbs)
 with dbs.begin() as db:
  db.add(Presence(user_id=user['id'],city='london',zone_id='world',updated_at=time.time()))
  db.add(Presence(user_id=stale['id'],city='london',zone_id='world',updated_at=time.time()-200))
  credit(db,user['id'],5,'qa_kind','local','pc')
  credit(db,user['id'],50,'qa_kind','local','xp','xp')
 r=c.get('/api/super-admin/live?city=london',headers=admin);assert r.status_code==200,r.text
 assert r.json()['online_users']==1 and r.json()['zones'][0]['online']==1
 assert not any(k in r.json()['zones'][0] for k in ['x','z','latitude','longitude'])
 r=c.get('/api/super-admin/overview',headers=admin);assert r.status_code==200,r.text
 assert next(row for row in r.json()['credit_activity'] if row['kind']=='qa_kind')['amount']==5
 with dbs.begin() as db:db.get(User,user['id']).suspended=True
 assert c.get('/api/super-admin/live',headers=admin).json()['online_users']==0
