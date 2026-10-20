import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from backend.api.main import app, local_buckets
from backend.api.db import Base, get_db
from backend.api.models import *
from backend.api.cli import seed
from backend.api.economy import credit, balance


@pytest.fixture
def system(tmp_path, monkeypatch):
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "core.db"),
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions.begin() as db:
        seed(db)

    def dependency():
        with sessions() as db:
            try:
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    import backend.api.main as main_module

    monkeypatch.setattr(main_module, "SessionLocal", sessions)
    app.dependency_overrides[get_db] = dependency
    local_buckets.clear()
    with TestClient(app, client=("qa-"+tmp_path.name, 50000)) as c:
        yield c, sessions
    app.dependency_overrides.clear()
    engine.dispose()


def register(c, name="alice"):
    r = c.post(
        "/api/auth/register",
        json={
            "email": name + "@example.test",
            "username": name,
            "password": "A secure test password 2026!",
            "adult": True,
            "accepted_terms": True,
        },
    )
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}, r.json()["user"]


def onboard(c, h, privacy="City Mode"):
    r = c.post(
        "/api/onboarding",
        headers=h,
        json={
            "city": "london",
            "interests": ["music"],
            "avatar": {"color": "#50ddab"},
            "privacy": privacy,
            "location_consent": False,
            "analytics_consent": True,
        },
    )
    assert r.status_code == 200, r.text
    assert (
        c.post("/api/world/enter", headers=h, json={"city": "london"}).status_code
        == 200
    )


def test_auth_onboarding_wallet_logout(system):
    c, db = system
    assert c.get("/api/me").status_code == 401
    h, u = register(c)
    onboard(c, h)
    onboard(c, h)
    w = c.get("/api/wallet", headers=h).json()
    assert (w["credits"], w["xp"]) == (50, 20)
    assert c.get("/api/admin/users", headers=h).status_code == 403
    assert (
        c.post(
            "/api/auth/login", json={"email": u["id"], "password": "wrong"}
        ).status_code
        == 401
    )
    assert c.post("/api/auth/logout", headers=h).status_code == 200
    assert c.get("/api/me", headers=h).status_code == 401


def test_collection_authority_mission_and_no_replay(system):
    c, sessions = system
    h, u = register(c)
    onboard(c, h)
    assert (
        c.post("/api/collectibles/london-local-5/claim", headers=h).status_code == 409
    )
    assert (
        c.post("/api/world/move", headers=h, json={"dx": 999, "dz": 0}).status_code
        == 422
    )
    assert (
        c.post(
            "/api/world/move", headers=h, json={"dx": 1, "dz": 0, "mode": "car"}
        ).status_code
        == 403
    )
    for i in range(4):
        with sessions.begin() as db:
            obj = db.get(Collectible, "london-local-" + str(i))
            p = db.get(Presence, u["id"])
            p.x = obj.x
            p.z = obj.z
        r = c.post("/api/collectibles/london-local-" + str(i) + "/claim", headers=h)
        assert r.status_code == 200, r.text
        assert c.post(
            "/api/collectibles/london-local-" + str(i) + "/claim", headers=h
        ).json()["already_claimed"]
    w = c.get("/api/wallet", headers=h).json()
    assert w["credits"] == 80 and w["xp"] == 100
    m = c.get("/api/missions", headers=h).json()
    assert m[0]["completed"]
    assert c.get("/api/passport", headers=h).status_code == 200


def test_concurrent_daily_reward_exactly_once(system):
    c, sessions = system
    h, u = register(c)
    onboard(c, h)
    with ThreadPoolExecutor(max_workers=6) as executor:
        replies = list(
            executor.map(lambda _: c.post("/api/rewards/daily", headers=h), range(6))
        )
    assert all(r.status_code == 200 for r in replies)
    assert c.get("/api/wallet", headers=h).json()["credits"] == 60
    with sessions() as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Ledger).where(Ledger.kind == "daily")
            )
            == 1
        )


def test_privacy_block_media_and_message_permissions(system):
    c, sessions = system
    a, ua = register(c, "alice")
    b, ub = register(c, "bob")
    d, ud = register(c, "david")
    for h in [a, b, d]:
        onboard(c, h)
    assert len(c.get("/api/world/london", headers=a).json()["players"]) == 2
    s = c.post(
        "/api/media/request",
        headers=a,
        json={"target_id": ub["id"], "kind": "liveface"},
    ).json()
    assert c.post("/api/media/" + s["id"] + "/token", headers=a).status_code == 403
    assert c.post("/api/media/" + s["id"] + "/accept", headers=a).status_code == 403
    assert c.post("/api/media/" + s["id"] + "/accept", headers=b).status_code == 200
    assert c.post("/api/media/" + s["id"] + "/token", headers=d).status_code == 404
    assert c.post("/api/media/" + s["id"] + "/token", headers=a).status_code == 503
    assert (
        c.post(
            "/api/messages/" + ub["id"], headers=a, json={"body": "Hello Bob"}
        ).status_code
        == 201
    )
    assert len(c.get("/api/messages/" + ua["id"], headers=b).json()) == 1
    assert c.get("/api/messages/" + ua["id"], headers=d).json() == []
    assert c.post("/api/social/" + ua["id"] + "/block", headers=b).status_code == 200
    assert c.get("/api/messages/" + ub["id"], headers=a).status_code == 403
    assert c.post("/api/media/" + s["id"] + "/token", headers=a).status_code == 403
    assert ub["id"] not in [
        p["id"] for p in c.get("/api/world/london", headers=a).json()["players"]
    ]
    onboard(c, d, "Ghost Mode")
    assert c.get("/api/world/london", headers=a).json()["players"] == []
    assert "latitude" not in c.get("/api/world/london", headers=b).text


def test_friends_crews_events_and_anonymisation(system):
    c, sessions = system
    a, ua = register(c, "alice")
    b, ub = register(c, "bob")
    onboard(c, a)
    onboard(c, b)
    assert c.post("/api/social/" + ub["id"] + "/friend", headers=a).status_code == 200
    assert c.post("/api/social/" + ua["id"] + "/accept", headers=b).status_code == 200
    crew = c.post(
        "/api/crews", headers=a, json={"name": "London explorers", "city": "london"}
    ).json()
    assert c.post("/api/crews/" + crew["id"] + "/join", headers=b).status_code == 200
    e = c.post(
        "/api/events",
        headers=a,
        json={
            "title": "Walking meetup",
            "city": "london",
            "starts_at": time.time() + 1000,
            "capacity": 2,
        },
    ).json()
    assert c.post("/api/events/" + e["id"] + "/join", headers=b).status_code == 200
    exp = c.get("/api/privacy/export", headers=a)
    assert (
        exp.status_code == 200
        and "password_hash" not in exp.text
        and "token_hash" not in exp.text
    )
    assert c.delete("/api/me", headers=a).status_code == 200
    assert c.get("/api/me", headers=a).status_code == 401


def test_ledger_atomic_rollback_conflict_and_overdraft(system):
    c, sessions = system
    h, u = register(c)
    onboard(c, h)
    with pytest.raises(RuntimeError):
        with sessions.begin() as db:
            credit(db, u["id"], 25, "test", "x", "k")
            raise RuntimeError("Abort transaction")
    assert c.get("/api/wallet", headers=h).json()["credits"] == 50
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        with sessions.begin() as db:
            credit(db, u["id"], -60, "spend", "x", "overdraft")
    with sessions.begin() as db:
        credit(db, u["id"], 10, "test", "x", "k")
    with pytest.raises(HTTPException):
        with sessions.begin() as db:
            credit(db, u["id"], 20, "test", "x", "k")


def test_authenticated_realtime_and_revoked_session(system):
    c, sessions = system
    a, ua = register(c, "alice")
    b, ub = register(c, "bob")
    onboard(c, a)
    onboard(c, b)
    with c.websocket_connect("/api/realtime") as ws:
        ws.send_json({"token": a["Authorization"][7:]})
        state = ws.receive_json()
        assert state["type"] == "state" and ub["id"] in [
            p["id"] for p in state["players"]
        ]
        assert "email" not in str(state) and "latitude" not in str(state)
        c.post("/api/auth/logout-all", headers=a)
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect(
            "/api/realtime", headers={"origin": "https://untrusted.example"}
        ) as ws:
            ws.send_json({"token": b["Authorization"][7:]})


def test_streaming_body_limit(system):
    c, _ = system
    r = c.post("/api/auth/login", content=b"x" * 262145)
    assert r.status_code == 413


def test_pending_business_owner_can_manage(system):
    c, _ = system
    a, ua = register(c, "alice")
    b, ub = register(c, "bob")
    data = {
        "name": "Owner Test Shop",
        "city": "london",
        "address": "Local test address",
        "latitude": 51.5,
        "longitude": -0.1,
    }
    r = c.post("/api/businesses", headers=a, json=data)
    assert r.status_code == 200
    id = r.json()["id"]
    assert c.get("/api/businesses/" + id).status_code == 404
    assert c.get("/api/businesses/" + id + "/manage", headers=a).status_code == 200
    assert c.get("/api/businesses/" + id + "/manage", headers=b).status_code == 404


def test_public_preview_excludes_players_and_cannot_claim(system):
    c, sessions = system
    headers, user = register(c, "previewplayer")
    onboard(c, headers)
    before = c.get("/api/wallet", headers=headers).json()
    response = c.get("/api/world-preview/london")
    assert response.status_code == 200
    preview = response.json()
    assert preview["preview"] is True and preview["simulated"] is True
    assert preview["players"] == []
    assert user["id"] not in response.text
    assert preview["collectibles"]
    item = preview["collectibles"][0]
    assert c.post("/api/collectibles/" + item["id"] + "/claim", json={}).status_code == 401
    assert c.get("/api/wallet", headers=headers).json() == before
    assert c.get("/api/world-preview/unknown-city").status_code == 422
