from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy import select
from backend.tests.test_core import system, register, onboard
from backend.api.economy import credit, balance
from backend.api.property_economy import Trade, Property, Offer
from backend.api.locations import CITIES
from backend.api.property_inventory import inventory


def explorer(c, sessions, name, xp):
    h, u = register(c, name)
    onboard(c, h)
    with sessions.begin() as db:
        credit(
            db,
            u["id"],
            xp - balance(db, u["id"], "xp"),
            "test",
            "property-test",
            str(uuid4()),
            "xp",
        )
    return h, u


def cities_test_rows():
    return [inventory(c["id"]) for c in CITIES]


def test_every_installed_map_has_distinct_inventory():
    maps = cities_test_rows()
    ids = [key for rows in maps for key in rows]
    assert all(maps) and len(ids) == len(set(ids))


def test_purchase_and_competing_offers(system):
    c, sessions = system
    a, alice = explorer(c, sessions, "alice", 4000)
    b, bob = explorer(c, sessions, "bob", 3000)
    d, dan = explorer(c, sessions, "dan", 3000)
    items = c.get("/api/properties/city/london", headers=a).json()["items"]

    def post(key, action, h, body):
        return c.post("/api/properties/" + key + "/" + action, headers=h, json=body)

    key, second = [r["id"] for r in items[:2]]
    req = {"amount": 2000, "request_key": str(uuid4())}
    r = post(key, "claim", a, req)
    assert r.status_code == 200, r.text
    assert post(key, "claim", a, req).json() == r.json()
    assert (
        post(second, "claim", a, {**req, "request_key": str(uuid4())}).json()["balance"]
        == 0
    )
    short = post(items[2]["id"], "claim", a, {**req, "request_key": str(uuid4())})
    assert short.json()["detail"]["shortfall"] == 2000
    assert len(c.get("/api/properties/portfolio", headers=a).json()) == 2
    studio = {"name": "Sera Villa", "board": "forest"}
    url = "/api/properties/" + key + "/studio"
    assert c.patch(url, headers=b, json=studio).status_code == 403
    assert c.patch(url, headers=a, json=studio).json()["name"] == "Sera Villa"
    bids = [post(key, "offer", h, {"amount": 3000}).json()["id"] for h in (b, d)]
    decide = "/api/properties/offers/" + bids[0]
    assert (
        c.post(
            decide,
            headers=a,
            json={"action": "counter", "amount": 2900, "expected_amount": 3000},
        ).status_code
        == 200
    )
    assert (
        c.post(
            decide, headers=b, json={"action": "accept", "expected_amount": 3000}
        ).status_code
        == 409
    )
    assert (
        c.post(
            decide, headers=b, json={"action": "accept", "expected_amount": 2900}
        ).json()["state"]
        == "accepted"
    )
    assert (
        c.post(
            decide, headers=b, json={"action": "accept", "expected_amount": 2900}
        ).status_code
        == 409
    )
    with sessions() as db:
        assert db.get(Property, key).owner == bob["id"]
        assert db.get(Offer, bids[1]).state == "superseded"
        assert balance(db, bob["id"], "xp") == 100
        assert balance(db, alice["id"], "xp") == 2900
        assert len(db.scalars(select(Trade)).all()) == 3
    assert c.patch(url, headers=a, json=studio).status_code == 403


def test_concurrent_buyers(system):
    c, sessions = system
    users = [explorer(c, sessions, name, 2000) for name in ("alice", "bob")]
    key = c.get("/api/properties/city/london", headers=users[0][0]).json()["items"][0][
        "id"
    ]

    def claim(user):
        return c.post(
            f"/api/properties/{key}/claim",
            headers=user[0],
            json={"amount": 2000, "request_key": str(uuid4())},
        ).status_code

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(claim, users)) == [200, 409]
    with sessions() as db:
        assert len(db.scalars(select(Trade)).all()) == 1
        assert sorted(balance(db, u["id"], "xp") for _, u in users) == [0, 2000]


def test_all_active_districts_and_price_override(system):
    from backend.api.discovery import catalog
    from backend.api.property_economy import (
        register as register_city,
        purchase,
        Purchase,
    )
    from backend.api.growth import select_starter
    from backend.api.models import User

    c, sessions = system
    with sessions.begin() as db:
        active = [
            d for d in catalog(db) if d["enabled"] and d["public"] and d["joinable"]
        ]
        assert active
        for i, city in enumerate(active):
            if i % 4 == 0:
                u = User(
                    username="testbuyer" + str(i),
                    email=f"buyer{i}@example.test",
                    password_hash="test-only",
                    onboarded=True,
                )
                db.add(u)
                db.flush()
                credit(db, u.id, 8000, "test", "inventory acceptance", "fixture", "xp")
            select_starter(db, u, city["id"], confirmed=True)
            count = register_city(db, city["id"])
            assert count == register_city(db, city["id"])
            p = db.scalar(
                select(Property).where(
                    Property.city == city["id"], Property.category != "venue"
                )
            )
            assert purchase(p.id, Purchase(amount=2000, request_key=uuid4()), u, db)[
                "receipt"
            ]
            assert p.owner == u.id
        assert len(list(db.scalars(select(Trade)))) == len(active)
    h, admin = register(c, "operator")
    with sessions.begin() as db:
        db.get(User, admin["id"]).role = "super_admin"
    r = c.get("/api/properties/admin/coverage", headers=h)
    assert all(d["registered"] == d["eligible"] for d in r.json())
    assert (
        c.put(
            "/api/properties/admin/prices",
            headers=h,
            json={
                "scope": "london",
                "category": "house",
                "amount": 4567,
                "enabled": True,
            },
        ).status_code
        == 200
    )


def test_private_entry_and_offer_rejections(system):
    c, sessions = system
    a, alice = explorer(c, sessions, "owner", 4000)
    b, bob = explorer(c, sessions, "visitor", 4000)
    key = c.get("/api/properties/city/london", headers=a).json()["items"][0]["id"]
    q = "/api/properties/" + key
    assert (
        c.post(
            q + "/claim", headers=a, json={"amount": 2000, "request_key": str(uuid4())}
        ).status_code
        == 200
    )
    assert (
        c.post("/api/buildings/home:" + key + "/enter", headers=b, json={}).status_code
        == 403
    )
    assert c.get("/api/properties/admin/overview", headers=b).status_code == 403
    bid = c.post(q + "/offer", headers=b, json={"amount": 2400}).json()["id"]
    decide = "/api/properties/offers/" + bid
    assert (
        c.post(
            decide, headers=a, json={"action": "reject", "expected_amount": 2400}
        ).json()["state"]
        == "rejected"
    )
    bid = c.post(q + "/offer", headers=b, json={"amount": 2400}).json()["id"]
    with sessions.begin() as db:
        db.get(Offer, bid).expires = 1
    assert (
        c.post(
            "/api/properties/offers/" + bid,
            headers=a,
            json={"action": "accept", "expected_amount": 2400},
        ).status_code
        == 409
    )
    with sessions() as db:
        assert (
            balance(db, bob["id"], "xp") == 4000
            and db.get(Property, key).owner == alice["id"]
        )


def test_reversal_requires_independent_review_and_is_exactly_once(system):
    from backend.api.models import User

    c, sessions = system
    h, u = explorer(c, sessions, "buyer", 2000)
    key = c.get("/api/properties/city/london", headers=h).json()["items"][0]["id"]
    t = c.post(
        "/api/properties/" + key + "/claim",
        headers=h,
        json={"amount": 2000, "request_key": str(uuid4())},
    ).json()["receipt"]
    admins = [register(c, n) for n in ("operator", "reviewer")]
    with sessions.begin() as db:
        for _, account in admins:
            db.get(User, account["id"]).role = "super_admin"
    base = "/api/properties/admin/trades/" + t
    assert (
        c.post(
            base + "/review",
            headers=admins[0][0],
            json={"reason": "Correct an erroneous test claim"},
        ).status_code
        == 200
    )
    assert c.post(base + "/reverse", headers=admins[0][0]).status_code == 403
    for _ in range(2):
        assert c.post(base + "/reverse", headers=admins[1][0]).json() == {
            "reversed": True
        }
    with sessions() as db:
        assert (
            db.get(Property, key).owner is None and balance(db, u["id"], "xp") == 2000
        )


def test_postgresql_competing_claims():
    import os, pytest
    from threading import Barrier
    from fastapi import HTTPException
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from backend.api.db import engine, Base, APP_ENV
    from backend.api.cli import seed
    from backend.api.models import User
    from backend.api.growth import select_starter
    from backend.api.property_economy import (
        purchase,
        Purchase,
        register as register_city,
    )

    if not os.getenv("DATABASE_URL", "").startswith("postgresql"):
        pytest.skip("Uses the existing disposable PostgreSQL CI service")
    assert APP_ENV == "test"
    schema = "property_race_" + uuid4().hex
    scoped = engine.execution_options(schema_translate_map={None: schema})
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        Base.metadata.create_all(scoped)
        with Session(scoped) as db, db.begin():
            seed(db)
            for account in ["buyer1", "buyer2"]:
                u = User(
                    id=account,
                    email=account + "@example.test",
                    username=account,
                    password_hash="test-only",
                    onboarded=True,
                )
                db.add(u)
                db.flush()
                select_starter(db, u, "london", confirmed=True)
                credit(db, u.id, 2000, "test", "pg-race", "fixture", "xp")
            register_city(db, "london")
            key = db.scalar(
                select(Property.id).where(
                    Property.city == "london", Property.category != "venue"
                )
            )
        barrier = Barrier(2)

        def buy(account):
            try:
                with Session(scoped) as db, db.begin():
                    u = db.get(User, account)
                    barrier.wait(timeout=10)
                    purchase(key, Purchase(amount=2000, request_key=uuid4()), u, db)
                return 200
            except HTTPException as exc:
                return exc.status_code

        with ThreadPoolExecutor(2) as pool:
            assert sorted(pool.map(buy, ["buyer1", "buyer2"])) == [200, 409]
        with Session(scoped) as db:
            assert len(db.scalars(select(Trade)).all()) == 1
            assert sorted(balance(db, a, "xp") for a in ["buyer1", "buyer2"]) == [
                0,
                2000,
            ]
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
