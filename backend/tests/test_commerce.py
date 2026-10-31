import hashlib
import hmac
import json
import time
import pytest
from fastapi import FastAPI, Header, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from backend.api import commerce as c
from backend.api.models import User, Ledger
from backend.api.economy import credit


@pytest.fixture
def commerce(tmp_path, monkeypatch):
    monkeypatch.setenv("PULSEPOINT_SECRET", "test-only-pulsepoint-secret-32-characters")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "commerce.db"),
        connect_args={"check_same_thread": False},
    )
    c.Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions.begin() as db:
        for id, role in [
            ("owner", "consumer"),
            ("other", "consumer"),
            ("player", "consumer"),
            ("player2", "consumer"),
            ("admin", "admin"),
        ]:
            db.add(
                User(
                    id=id,
                    email=id + "@example.test",
                    username=id,
                    password_hash="not-used-in-domain-tests",
                    role=role,
                )
            )

    def dep():
        with sessions() as db:
            try:
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def auth(x_user: str = Header(default="player"), db=Depends(c.get_db)):
        return db.get(User, x_user)

    app = FastAPI()
    app.include_router(c.router)
    app.dependency_overrides[c.get_db] = dep
    app.dependency_overrides[c.current_user] = auth
    with TestClient(app, client=("qa-"+tmp_path.name, 50000)) as client:
        yield client, sessions
    engine.dispose()


def post(client, path, body={}, who="owner"):
    return client.post("/api" + path, json=body, headers={"x-user": who})


def setup_business(commerce):
    client, sessions = commerce
    r = post(
        client,
        "/businesses",
        {
            "name": "Test Cafe",
            "city": "london",
            "address": "Test-only store",
            "latitude": 51.5,
            "longitude": -0.1,
        },
    )
    assert r.status_code == 200, r.text
    b = r.json()["id"]
    assert (
        post(
            client, f"/admin/businesses/{b}/verify", {"approved": True}, "admin"
        ).status_code
        == 200
    )
    with sessions.begin() as db:
        c.fund(db, db.get(c.Business, b), 100, "test_fixture", "test", "test:" + b)
    return b


def setup_campaign(commerce, reward=10, budget=20):
    client, _ = commerce
    b = setup_business(commerce)
    r = post(
        client,
        f"/businesses/{b}/campaigns",
        {
            "title": "Visit test cafe",
            "reward_credits": reward,
            "budget_credits": budget,
        },
    )
    assert r.status_code == 200, r.text
    camp = r.json()["id"]
    assert post(client, f"/campaigns/{camp}/publish").status_code == 200
    return b, camp


def token(client, camp, user="player"):
    r = post(client, f"/campaigns/{camp}/pulsepoint", {"user_id": user})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def visit(client, t, who="player", **kw):
    return post(
        client,
        "/visits/verify",
        {
            "token": t,
            "latitude": 51.5,
            "longitude": -0.1,
            "accuracy_m": 5,
            "consent": True,
            **kw,
        },
        who,
    )


def test_tenant_and_admin_authorization(commerce):
    client, _ = commerce
    b = setup_business(commerce)
    assert (
        client.get(
            f"/api/businesses/{b}/analytics", headers={"x-user": "other"}
        ).status_code
        == 404
    )
    assert (
        post(
            client,
            f"/businesses/{b}/products",
            {"name": "Tea", "kind": "product", "price_pence": 300},
            "other",
        ).status_code
        == 404
    )
    assert (
        post(
            client, f"/admin/businesses/{b}/verify", {"approved": False}, "owner"
        ).status_code
        == 403
    )
    assert "latitude" not in client.get(f"/api/businesses/{b}").text


def test_visit_replay_budget_daily_and_gps_privacy(commerce):
    client, sessions = commerce
    b, camp = setup_campaign(commerce, reward=10, budget=10)
    t = token(client, camp)
    r = visit(client, t)
    assert r.status_code == 200, r.text
    assert r.json()["credits_awarded"] == 0 and r.json()["xp_awarded"] == 10
    assert visit(client, t).status_code == 409
    assert visit(client, token(client, camp)).status_code == 409
    assert visit(client, token(client, camp, "player2"), "player2").status_code == 409
    with sessions() as db:
        assert (
            db.scalar(select(func.sum(Ledger.amount)).where(Ledger.user_id == "player"))
            == 10
        )
        assert db.get(c.Campaign, camp).spent_credits == 10
        assert not hasattr(db.scalar(select(c.Visit)), "latitude")
    a = client.get(f"/api/businesses/{b}/analytics", headers={"x-user": "owner"}).json()
    assert a["verified_visits"] == 1 and a["credits_awarded"] == 0 and a["xp_awarded"] == 10


def test_qr_wrong_user_forged_expired_and_consent(commerce):
    client, sessions = commerce
    _, camp = setup_campaign(commerce)
    t = token(client, camp)
    assert visit(client, t, "player2").status_code == 403
    assert visit(client, t[:-1] + ("1" if t[-1] != "1" else "2")).status_code == 400
    assert visit(client, t, consent=False).status_code == 422
    assert visit(client, t, latitude=52).status_code == 422
    assert visit(client, t, accuracy_m=51).status_code == 422
    claims = c.unsign(t)
    with sessions.begin() as db:
        db.get(c.PulsePoint, claims["id"]).expires_at = time.time() - 1
    assert visit(client, t).status_code == 400


def test_reserve_release_and_no_unfunded_publish(commerce):
    client, sessions = commerce
    b, camp = setup_campaign(commerce, budget=100)
    with sessions() as db:
        assert db.get(c.Business, b).funds == 0
    t = token(client, camp)
    assert visit(client, t).status_code == 200
    assert post(client, f"/campaigns/{camp}/close").status_code == 200
    assert post(client, f"/campaigns/{camp}/close").status_code == 200
    with sessions() as db:
        assert db.get(c.Business, b).funds == 90
    r = post(
        client,
        f"/businesses/{b}/campaigns",
        {"title": "Too expensive", "reward_credits": 10, "budget_credits": 100},
    )
    id = r.json()["id"]
    assert post(client, f"/campaigns/{id}/publish").status_code == 409


def test_perks_debit_idempotence_merchant_confirmation(commerce):
    client, sessions = commerce
    b = setup_business(commerce)
    with sessions.begin() as db:
        credit(db, "player", 20, "purchase", "local-payment", "local-payment")
    o = post(
        client, f"/businesses/{b}/offers", {"title": "Free tea", "cost_credits": 10}
    ).json()["id"]
    r = post(client, f"/offers/{o}/redeem", {"request_id": "same-request"}, "player")
    assert r.status_code == 200, r.text
    p = r.json()["id"]
    assert (
        post(
            client, f"/offers/{o}/redeem", {"request_id": "same-request"}, "player"
        ).json()["id"]
        == p
    )
    assert post(client, f"/perks/{p}/use", {}, "other").status_code == 404
    assert post(client, f"/perks/{p}/use").status_code == 200
    assert post(client, f"/perks/{p}/use").status_code == 409
    with sessions() as db:
        assert (
            db.scalar(select(func.sum(Ledger.amount)).where(Ledger.user_id == "player"))
            == 10
        )


def test_payments_fail_closed(commerce):
    client, _ = commerce
    assert post(client, "/payments/checkout", {"sku": "credits_500"}).status_code == 503
    assert post(client, "/payments/webhook", {}).status_code == 503


def signed(client, event, secret):
    payload = json.dumps(event)
    ts = int(time.time())
    sig = hmac.new(
        secret.encode(), f"{ts}.{payload}".encode(), hashlib.sha256
    ).hexdigest()
    return client.post(
        "/api/payments/webhook",
        content=payload,
        headers={"stripe-signature": f"t={ts},v1={sig}"},
    )


def test_signed_webhook_payment_once_and_tampering(commerce, monkeypatch):
    client, sessions = commerce
    secret = "whsec_test_only"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    with sessions.begin() as db:
        db.add(
            c.Payment(
                id="pay1",
                user_id="player",
                sku="credits_500",
                amount_pence=499,
                credits=500,
                provider_id="cs_test",
                request_key="test-payment",
            )
        )
    event = {
        "id": "evt_1",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test",
                "object": "checkout.session",
                "metadata": {"payment_id": "pay1"},
                "payment_status": "paid",
                "amount_total": 499,
                "currency": "gbp",
            }
        },
    }
    assert (
        client.post(
            "/api/payments/webhook", json=event, headers={"stripe-signature": "garbage"}
        ).status_code
        == 400
    )
    assert signed(client, event, secret).status_code == 200
    assert signed(client, event, secret).json()["duplicate"] is True
    event["id"] = "evt_2"
    assert signed(client, event, secret).status_code == 200
    with sessions() as db:
        assert (
            db.scalar(select(func.sum(Ledger.amount)).where(Ledger.user_id == "player"))
            == 500
        )
        assert db.get(c.Payment, "pay1").status == "paid"


def test_funding_ledger_immutable(commerce):
    _, sessions = commerce
    b = setup_business(commerce)
    with sessions() as db:
        row = db.scalar(select(c.FundingLedger).where(c.FundingLedger.business_id == b))
        row.amount = 999
        with pytest.raises(ValueError, match="immutable"):
            db.flush()


def test_simultaneous_qr_claims_award_once(commerce):
    from concurrent.futures import ThreadPoolExecutor

    client, sessions = commerce
    _, camp = setup_campaign(commerce)
    t = token(client, camp)
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(lambda _: visit(client, t).status_code, range(4)))
    assert sorted(statuses) == [200, 409, 409, 409]
    with sessions() as db:
        assert (
            db.scalar(select(func.sum(Ledger.amount)).where(Ledger.user_id == "player"))
            == 10
        )


def test_webhook_amount_mismatch_rolls_back_then_funds_once(commerce, monkeypatch):
    client, sessions = commerce
    b = setup_business(commerce)
    secret = "whsec_test_only"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    with sessions.begin() as db:
        db.add(
            c.Payment(
                id="payfund",
                user_id="owner",
                business_id=b,
                sku="campaign_1000",
                amount_pence=1000,
                credits=1000,
                provider_id="cs_fund",
                request_key="fund-payment",
            )
        )
    event = {
        "id": "evt_fund",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_fund",
                "object": "checkout.session",
                "metadata": {"payment_id": "payfund"},
                "payment_status": "paid",
                "amount_total": 1,
                "currency": "gbp",
            }
        },
    }
    assert signed(client, event, secret).status_code == 400
    with sessions() as db:
        assert db.get(c.PaymentEvent, "evt_fund") is None
    event["data"]["object"]["amount_total"] = 1000
    assert signed(client, event, secret).status_code == 200
    assert signed(client, event, secret).status_code == 200
    with sessions() as db:
        assert db.get(c.Business, b).funds == 1100
