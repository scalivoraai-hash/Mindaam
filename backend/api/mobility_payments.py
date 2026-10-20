"""Forward-only mobility currency policy; prices retain their configured amounts."""
from fastapi import HTTPException
from sqlalchemy import select
from .models import User
from .economy import balance, credit

XP_KINDS = {'car': 'car_rental_xp', 'bike': 'bike_rental_xp', 'ebike': 'bike_rental_xp', 'bus': 'bus_ticket_xp'}

def currency(kind):
    return 'xp' if kind in XP_KINDS else 'credits'

def charge(db, user_id, kind, amount, source, key, expected_currency):
    denomination = currency(kind)
    # Callers already hold this lock through eligibility, debit and entitlement creation.
    db.scalar(select(User.id).where(User.id == user_id).with_for_update())
    if expected_currency != denomination and not (denomination == 'credits' and expected_currency is None):
        raise HTTPException(409, {'code': 'CURRENCY_CHANGED', 'currency': denomination,
                                 'message': 'Review the current price and payment currency before confirming.'})
    available = balance(db, user_id, denomination)
    if amount > available and denomination == 'xp':
        raise HTTPException(409, {'code': 'INSUFFICIENT_XP', 'required': amount, 'balance': available,
                                 'shortfall': amount-available, 'message': f'Not enough XP. You need {amount-available} more XP.'})
    if amount:
        credit(db, user_id, -amount, XP_KINDS.get(kind, 'vehicle_rental'), source, key, currency=denomination)
    return denomination
