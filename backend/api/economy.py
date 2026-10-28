from fastapi import HTTPException
from sqlalchemy import select, func
from .models import User, Ledger, Audit, Config


def config(db, key, default):
    row = db.get(Config, key)
    return row.value if row else default


def balance(db, user_id, currency="credits"):
    return int(
        db.scalar(
            select(func.coalesce(func.sum(Ledger.amount), 0)).where(
                Ledger.user_id == user_id, Ledger.currency == currency
            )
        )
        or 0
    )


def credit(db, user_id, amount, kind, source, key, currency="credits"):
    if (
        isinstance(amount, bool)
        or not isinstance(amount, int)
        or currency not in {"credits", "xp"}
    ):
        raise HTTPException(400, "Invalid ledger amount or currency")
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    row = db.scalar(
        select(Ledger).where(
            Ledger.user_id == user_id,
            Ledger.currency == currency,
            Ledger.idempotency_key == key,
        )
    )
    if row:
        if row.amount != amount or row.kind != kind or row.source != source:
            raise HTTPException(409, "Idempotency key conflict")
        return row
    if currency == 'credits' and amount < 0 and kind != 'payment_reversal':
        from .payment_settlement import require_spending
        require_spending(db, user_id)
    before = balance(db, user_id, currency)
    if before + amount < 0:
        raise HTTPException(409, "Insufficient Credits")
    row = Ledger(
        user_id=user_id,
        currency=currency,
        amount=amount,
        kind=kind,
        source=source,
        idempotency_key=key,
        previous_balance=before,
        balance=before + amount,
    )
    db.add(row)
    db.add(
        Audit(
            actor_id=user_id,
            action="ledger.post",
            target=source,
            details={"currency": currency, "amount": amount, "kind": kind},
        )
    )
    db.flush()
    if currency == 'credits' and amount > 0:
        from .payment_settlement import settle
        settle(db, user_id)
    return row
