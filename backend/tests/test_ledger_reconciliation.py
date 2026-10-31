from types import SimpleNamespace
from backend.api.ledger_reconciliation import review_rows

def row(i,n,kind):return SimpleNamespace(id=str(i),created_at=i,user_id='local-fixture',currency='credits',amount=n,kind=kind)
def test_conservative_review_protects_paid_transferred_and_ambiguous_value():
 rows=[row(1,100,'mission'),row(2,70,'purchase'),row(3,20,'event_ticket_sale'),row(4,30,'unclassified'),row(5,-40,'social_gift')]
 result=review_rows(rows);account=result['accounts'][0]
 assert account['current_pc']==180 and account['candidate_pc_for_owner_review']==60
 assert account['protected_or_ambiguous_lifetime_pc']==120
 assert result['adjustments_applied'] is False and result['owner_approval_required']
 assert rows[0].amount==100

def test_spent_gameplay_and_refunds_are_not_confiscated():
 rows=[row(1,100,'welcome'),row(2,100,'purchase'),row(3,-150,'event_ticket'),row(4,50,'event_ticket_refund')]
 assert review_rows(rows)['totals']['candidate_pc_for_owner_review']==0

def test_account_report_preserves_ambiguous_value_and_identifies_exact_snapshot():
 rows=[row(1,100,'mission'),row(2,50,'purchase'),row(3,20,'promotion'),row(4,-10,'event_ticket')]
 result=review_rows(rows,{'2'})['accounts'][0]
 assert result['verified_purchase_pc']==50 and result['legacy_test_promotional_pc']==20
 assert result['candidate_pc_for_owner_review']==90 and result['proposed_pc']==70
 assert len(result['ledger_sha256'])==64 and result['ledger_entries']==4
 assert result['ledger_sha256']!=review_rows(rows+[row(5,1,'daily')])['accounts'][0]['ledger_sha256']

from backend.tests.test_core import system,register

def test_purchase_classification_requires_matching_paid_provider_record(system):
 from backend.api.models import Ledger
 from backend.api.commerce import Payment
 from backend.api.ledger_reconciliation import inspect
 from backend.api.economy import credit
 c,sessions=system;headers,user=register(c)
 with sessions.begin() as db:
  db.add(Payment(id='review-paid',user_id=user['id'],sku='credits',amount_pence=100,credits=50,provider_id='cs_test_review',status='paid',request_key='review-paid'))
  db.add(Payment(id='review-pending',user_id=user['id'],sku='credits',amount_pence=100,credits=30,provider_id='cs_test_pending',status='pending',request_key='review-pending'))
  credit(db,user['id'],50,'purchase','review-paid','payment:review-paid')
  credit(db,user['id'],30,'purchase','review-pending','payment:review-pending')
 with sessions() as db:
  result=inspect(db)['accounts'][0]
  assert result['verified_purchase_pc']==50 and result['purchase_ledger_pc']==80
  assert result['protected_or_ambiguous_lifetime_pc']==80
  assert result['candidate_pc_for_owner_review']==0 and result['ledger_balance_consistent']
