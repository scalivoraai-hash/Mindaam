"""Explicit local payment/history fixtures; never used by application runtime."""
from backend.api.economy import credit, balance
from backend.api.models import Ledger

def purchased_fixture(user_id, amount=50, sessions=None):
    if sessions is None:
        from backend.api.main import SessionLocal
        sessions=SessionLocal
    with sessions.begin() as db:
        credit(db,user_id,amount,'purchase','local-payment-fixture','local-payment-fixture')

def historical_gameplay_fixture(db,user_id,amount,key):
    # Reconstruct an immutable pre-policy row to test eligibility/reconciliation.
    before=balance(db,user_id)
    db.add(Ledger(user_id=user_id,currency='credits',amount=amount,kind='mission',source=key,idempotency_key=key,previous_balance=before,balance=before+amount))
    db.flush()
