import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from backend.api import subscriptions as s
from backend.api.models import Config, Entitlement, Ledger, User

PLAN = {
    "id": "pulse_plus",
    "name": "Pulse+",
    "audience": "consumer",
    "stripe_price_id": "price_test123",
    "amount_pence": 499,
    "currency": "gbp",
    "interval": "month",
    "credits": 100,
    "features": ["Monthly credits"],
}


@pytest.fixture
def billing(tmp_path, monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.setenv("STRIPE_SUBSCRIPTION_WEBHOOK_SECRET", "whsec_subscription_test")
    monkeypatch.setenv("PUBLIC_APP_URL", "https://app.example.test")
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "billing.db"),
        connect_args={"check_same_thread": False},
    )
    s.Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions.begin() as db:
        for id in ("player", "other", "admin"):
            db.add(
                User(
                    id=id,
                    email=id + "@example.test",
                    username=id,
                    password_hash="test-only",
                    role="admin" if id == "admin" else "consumer",
                )
            )
        db.add(Config(key="subscription_catalog", value={"plans": [PLAN]}))

    def dep():
        with sessions() as db:
            try:
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def auth(x_user: str = Header(default="player"), db=Depends(s.get_db)):
        return db.get(User, x_user)

    def admin(u=Depends(auth)):
        if u.role != "admin":
            raise HTTPException(403)
        return u

    app = FastAPI()
    app.include_router(s.router)
    app.dependency_overrides[s.get_db] = dep
    app.dependency_overrides[s.current_user] = auth
    app.dependency_overrides[s.require_admin] = admin
    with TestClient(app, client=("qa-"+tmp_path.name, 50000)) as client:
        yield client, sessions
    engine.dispose()


def add_subscription(sessions):
    with sessions.begin() as db:
        db.add(
            s.CustomerSubscription(
                id="local_sub",
                user_id="player",
                plan_id="pulse_plus",
                plan=PLAN,
                request_key="test-key",
                checkout_id="cs_test",
                provider_id="sub_test",
                customer_id="cus_test",
            )
        )


def signed(client, kind, obj, event_id="evt_1", created=None):
    payload = json.dumps(
        {
            "id": event_id,
            "object": "event",
            "created": created or int(time.time()),
            "type": kind,
            "data": {"object": obj},
        }
    )
    ts = int(time.time())
    sig = hmac.new(
        b"whsec_subscription_test", f"{ts}.{payload}".encode(), hashlib.sha256
    ).hexdigest()
    return client.post(
        "/api/subscriptions/webhook",
        content=payload,
        headers={"stripe-signature": f"t={ts},v1={sig}"},
    )


def invoice(id="in_test", end=None):
    now = int(time.time())
    return {
        "id": id,
        "subscription": "sub_test",
        "customer": "cus_test",
        "status": "paid",
        "currency": "gbp",
        "amount_paid": 499,
        "amount_remaining": 0,
        "billing_reason": "subscription_cycle",
        "lines": {
            "data": [
                {
                    "price": {"id": "price_test123"},
                    "amount": 499,
                    "period": {"start": now - 10, "end": end or now + 86400},
                    "quantity": 1,
                }
            ]
        },
    }


def test_fail_closed_and_catalog_authorization(billing):
    client, sessions = billing
    assert client.get("/api/subscriptions/plans").json()["configured"] is False
    assert "stripe_price_id" not in client.get("/api/subscriptions/plans").text
    assert (
        client.post(
            "/api/subscriptions/checkout", json={"plan_id": "pulse_plus"}
        ).status_code
        == 503
    )
    assert (
        client.put("/api/admin/subscriptions/plans", json={"plans": []}).status_code
        == 403
    )
    assert (
        client.put(
            "/api/admin/subscriptions/plans",
            json={"plans": [PLAN, PLAN]},
            headers={"x-user": "admin"},
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/admin/subscriptions/plans",
            json={"plans": []},
            headers={"x-user": "admin"},
        ).status_code
        == 200
    )
    assert client.get("/api/subscriptions/plans").json()["plans"] == []


def test_checkout_and_portal_ownership(billing, monkeypatch):
    import stripe

    client, sessions = billing
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    calls = []
    monkeypatch.setattr(
        stripe.Price,
        "retrieve",
        lambda *args, **kwargs: {
            "active": True,
            "unit_amount": 499,
            "currency": "gbp",
            "recurring": {"interval": "month", "interval_count": 1},
        },
    )

    def checkout(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id="cs_test", url="https://checkout.stripe.com/test")

    monkeypatch.setattr(stripe.checkout.Session, "create", checkout)
    data = {"plan_id": "pulse_plus", "request_id": "unique-request"}
    response = client.post("/api/subscriptions/checkout", json=data)
    assert response.status_code == 200, response.text
    id = response.json()["subscription_id"]
    assert (
        client.post("/api/subscriptions/checkout", json=data).json() == response.json()
    )
    assert len(calls) == 1
    assert (
        client.post(
            "/api/subscriptions/checkout",
            json={"plan_id": "pulse_plus", "request_id": "different-request"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/subscriptions/{id}/portal", headers={"x-user": "other"}
        ).status_code
        == 404
    )
    assert client.get("/api/subscriptions", headers={"x-user": "other"}).json() == []
    assert client.post(f"/api/subscriptions/{id}/portal").status_code == 409
    with sessions() as db:
        assert db.get(Entitlement, ("player", "pulse_plus")) is None
    obj = {
        "id": "cs_test",
        "mode": "subscription",
        "metadata": {"pulse_subscription_id": id},
        "subscription": "sub_test",
        "customer": "cus_test",
    }
    assert signed(client, "checkout.session.completed", obj).status_code == 200
    assert client.get("/api/subscriptions").json()[0]["active"] is False
    monkeypatch.setattr(
        stripe.billing_portal.Session,
        "create",
        lambda **kwargs: SimpleNamespace(url="https://billing.stripe.com/test"),
    )
    assert client.post(f"/api/subscriptions/{id}/portal").status_code == 200


def test_signed_invoices_grant_once_per_invoice_and_reject_tamper(billing):
    client, sessions = billing
    add_subscription(sessions)
    obj = invoice()
    assert client.post("/api/subscriptions/webhook", json=obj).status_code == 400
    assert signed(client, "invoice.paid", obj).status_code == 200
    assert signed(client, "invoice.paid", obj).json()["duplicate"] is True
    assert signed(client, "invoice.paid", obj, "evt_2").status_code == 200
    with sessions() as db:
        assert db.scalar(select(func.sum(Ledger.amount))) == 100
        assert (
            db.get(Entitlement, ("player", "pulse_plus")).expires_at
            == obj["lines"]["data"][0]["period"]["end"]
        )
    second = invoice("in_next", end=int(time.time()) + 172800)
    assert signed(client, "invoice.paid", second, "evt_3").status_code == 200
    with sessions() as db:
        assert db.scalar(select(func.sum(Ledger.amount))) == 200
        assert db.scalar(select(func.count()).select_from(s.SubscriptionInvoice)) == 2


def test_failure_cancellation_and_stale_events_never_extend_unpaid_time(billing):
    client, sessions = billing
    add_subscription(sessions)
    now = int(time.time())
    assert signed(client, "invoice.paid", invoice(), created=now).status_code == 200
    assert (
        signed(
            client,
            "invoice.payment_failed",
            invoice("in_failed"),
            "evt_failed",
            now + 1,
        ).status_code
        == 200
    )
    row = client.get("/api/subscriptions").json()[0]
    assert row["status"] == "past_due" and row["active"] is True
    update = {
        "id": "sub_test",
        "customer": "cus_test",
        "status": "active",
        "cancel_at_period_end": True,
    }
    assert (
        signed(
            client,
            "customer.subscription.updated",
            update,
            "evt_cancel_requested",
            now + 2,
        ).status_code
        == 200
    )
    assert client.get("/api/subscriptions").json()[0]["cancel_at_period_end"] is True
    # End of paid period is sufficient to expire access even when no webhook arrives.
    with sessions.begin() as db:
        db.get(s.CustomerSubscription, "local_sub").paid_through = now - 1
    assert client.get("/api/subscriptions").json()[0]["active"] is False
    ended = {**update, "status": "canceled", "ended_at": now - 1}
    assert (
        signed(
            client, "customer.subscription.deleted", ended, "evt_deleted", now + 3
        ).status_code
        == 200
    )
    assert (
        signed(
            client, "customer.subscription.updated", update, "evt_old", now + 1
        ).status_code
        == 200
    )
    assert (
        signed(client, "invoice.paid", invoice(), "evt_old_invoice", now).status_code
        == 200
    )
    row = client.get("/api/subscriptions").json()[0]
    assert row["status"] == "canceled" and row["active"] is False
    with sessions() as db:
        assert db.get(Entitlement, ("player", "pulse_plus")).expires_at <= now
        assert db.scalar(select(func.sum(Ledger.amount))) == 100


def test_invalid_invoice_rolls_back_event_and_unrelated_payments_ignored(billing):
    client, sessions = billing
    add_subscription(sessions)
    obj = invoice()
    obj["customer"] = "cus_attacker"
    assert signed(client, "invoice.paid", obj).status_code == 400
    with sessions() as db:
        assert db.get(s.SubscriptionEvent, "evt_1") is None
    obj["customer"] = "cus_test"
    obj["lines"]["data"][0]["price"]["id"] = "price_wrong"
    assert signed(client, "invoice.paid", obj).status_code == 400
    assert (
        signed(
            client,
            "checkout.session.completed",
            {"id": "cs_other", "mode": "payment"},
            "evt_unrelated",
        ).status_code
        == 200
    )
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Ledger)) == 0


def test_price_mismatch_never_creates_checkout(billing, monkeypatch):
    import stripe

    client, sessions = billing
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(
        stripe.Price,
        "retrieve",
        lambda *args, **kwargs: {
            "active": True,
            "unit_amount": 999,
            "currency": "gbp",
            "recurring": {"interval": "month", "interval_count": 1},
        },
    )
    assert (
        client.post(
            "/api/subscriptions/checkout", json={"plan_id": "pulse_plus"}
        ).status_code
        == 503
    )
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(s.CustomerSubscription)) == 0


@pytest.mark.parametrize(
    "change",
    ["underpaid", "out_of_band", "wrong_line_amount", "remaining", "invalid_period"],
)
def test_invoice_payment_amount_and_period_validated_before_grants(billing, change):
    client, sessions = billing
    add_subscription(sessions)
    obj = invoice()
    if change == "underpaid":
        obj["amount_paid"] = 0
    elif change == "out_of_band":
        obj["paid_out_of_band"] = True
    elif change == "wrong_line_amount":
        obj["lines"]["data"][0]["amount"] = 1
    elif change == "remaining":
        obj["amount_remaining"] = 499
    else:
        obj["lines"]["data"][0]["period"]["start"] = "invalid"
    assert signed(client, "invoice.paid", obj).status_code == 400
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Ledger)) == 0
        assert db.get(s.SubscriptionEvent, "evt_1") is None
