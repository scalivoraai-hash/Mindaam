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
