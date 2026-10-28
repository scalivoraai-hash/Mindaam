"""Recover refunded consumer Credits without mutating ledger history or going negative."""
import math
import os
from fastapi import HTTPException
from sqlalchemy import select


def configured():
    key = os.getenv('STRIPE_SECRET_KEY', '')
    sandbox = os.getenv('APP_ENV', 'local') != 'production'
    return bool(key and os.getenv('STRIPE_WEBHOOK_SECRET') and
                (not sandbox or key.startswith(('sk_test_', 'rk_test_'))))


def target(payment):
    refund = payment.refunded_pence or 0
    lost = (payment.dispute_pence or 0) if payment.dispute_status == 'lost' else 0
    return min(payment.credits, math.ceil(payment.credits * min(payment.amount_pence, refund + lost) / payment.amount_pence))


def summary(db, user_id):
    from .commerce import Payment
    rows = db.scalars(select(Payment).where(Payment.user_id == user_id, Payment.business_id == None))
    due = 0
    disputed = False
    for p in rows:
        disputed |= bool(p.dispute_status and p.dispute_status not in ('won', 'lost', 'warning_closed'))
        if p.status == 'paid':
            due += max(0, target(p) - (p.reversed_credits or 0))
    return {'pending_recovery': due, 'disputed': disputed, 'spending_paused': disputed or due > 0}


def require_spending(db, user_id):
    if summary(db, user_id)['spending_paused']:
        raise HTTPException(409, 'Credit spending is paused while a payment dispute or refund balance is being resolved. Review Wallet.')


def settle(db, user_id):
    # Caller holds the user row lock. Payment state is mutable; all money entries are append-only.
    from .commerce import Payment
    from .economy import balance, credit
    for p in db.scalars(select(Payment).where(Payment.user_id == user_id, Payment.business_id == None, Payment.status == 'paid').order_by(Payment.created_at, Payment.id).with_for_update()):
        due = max(0, target(p) - (p.reversed_credits or 0))
        amount = min(due, balance(db, user_id))
        if amount:
            p.reversed_credits = (p.reversed_credits or 0) + amount
            credit(db, user_id, -amount, 'payment_reversal', p.id, f'payment-reversal:{p.id}:{p.reversed_credits}')
    db.flush()
