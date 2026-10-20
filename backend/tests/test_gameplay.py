import time
import pytest
from fastapi import FastAPI, Depends, Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from backend.api import gameplay as g, social, world, media
from backend.api.models import (
    User,
    Crew,
    CrewMember,
    Social,
    Collectible,
    Claim,
    Mission,
    MissionCompletion,
    Presence,
    Ledger,
)


@pytest.fixture
def game(tmp_path):
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "game.db"),
        connect_args={"check_same_thread": False},
    )
    g.Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions.begin() as db:
        for name in ["owner", "member", "outsider", "admin", "mod"]:
            db.add(
                User(
                    id=name,
                    username=name,
                    email=name + "@example.test",
                    password_hash="unused",
                    role="admin" if name == "admin" else "consumer",
                    onboarded=True,
                )
            )
        db.flush()
        db.add(
            Crew(
                id="private",
                name="Private Crew",
                city="london",
                owner_id="owner",
                private=True,
            )
        )
        db.flush()
        for name, role in [
            ("owner", "owner"),
            ("member", "member"),
            ("mod", "moderator"),
        ]:
            db.add(CrewMember(crew_id="private", user_id=name, role=role))

    def dep():
        with sessions() as db:
            try:
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def auth(x_user: str = Header(default="owner"), db=Depends(g.get_db)):
        return db.get(User, x_user)

    app = FastAPI()
    app.include_router(g.router)
    app.include_router(social.router)
    app.include_router(world.router)
    app.include_router(media.router)
    app.dependency_overrides[g.get_db] = dep
    app.dependency_overrides[g.current_user] = auth
    with TestClient(app, client=("qa-"+tmp_path.name, 50000)) as client:
        yield client, sessions
    engine.dispose()


def test_private_crew_invitation_authorization_block_and_replay(game):
    c, s = game
    assert (
        c.get("/api/crews/private/messages", headers={"x-user": "outsider"}).status_code
        == 404
    )
    assert (
        c.post(
            "/api/crews/private/invitations",
            json={"user_id": "outsider"},
            headers={"x-user": "member"},
        ).status_code
        == 403
    )
    invite = c.post(
        "/api/crews/private/invitations", json={"user_id": "outsider"}
    ).json()
    assert (
        c.post("/api/crews/private/invitations", json={"user_id": "outsider"}).json()[
            "id"
        ]
        == invite["id"]
    )
    path = "/api/crew-invitations/" + invite["id"] + "/accept"
    assert c.post(path, headers={"x-user": "member"}).status_code == 404
    with s.begin() as db:
        db.add(Social(actor="outsider", target="owner", kind="block"))
    assert c.get("/api/crew-invitations", headers={"x-user": "outsider"}).json() == []
    assert c.post(path, headers={"x-user": "outsider"}).status_code == 403
    with s.begin() as db:
        db.delete(db.scalar(select(Social)))
    for _ in range(2):
        assert c.post(path, headers={"x-user": "outsider"}).status_code == 200
    with s() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(CrewMember)
                .where(CrewMember.user_id == "outsider")
            )
            == 1
        )


def test_crew_message_storage_idempotency_block_and_roles(game):
    c, s = game
    path = "/api/crews/private/messages"
    first = c.post(
        path, json={"body": "Meet at the plaza", "request_id": "message-one"}
    ).json()
    assert (
        c.post(
            path, json={"body": "Meet at the plaza", "request_id": "message-one"}
        ).json()["id"]
        == first["id"]
    )
    assert (
        c.post(path, json={"body": "Changed", "request_id": "message-one"}).status_code
        == 409
    )
    assert len(c.get(path, headers={"x-user": "member"}).json()) == 1
    with s.begin() as db:
        db.add(Social(actor="member", target="owner", kind="block"))
    assert c.get(path, headers={"x-user": "member"}).json() == []
    assert (
        c.patch(
            "/api/crews/private/members/member",
            json={"role": "moderator"},
            headers={"x-user": "mod"},
        ).status_code
        == 403
    )
    assert (
        c.delete(
            "/api/crews/private/members/owner", headers={"x-user": "mod"}
        ).status_code
        == 409
    )
    assert (
        c.delete(
            "/api/crews/private/members/mod", headers={"x-user": "member"}
        ).status_code
        == 403
    )
    assert (
        c.delete(
            "/api/crews/private/members/member", headers={"x-user": "member"}
        ).status_code
        == 200
    )
    assert (
        c.post(
            path, json={"body": "No longer joined"}, headers={"x-user": "member"}
        ).status_code
        == 404
    )


def test_admin_authoring_schedule_cap_treasure_mission_and_replay(game):
    c, s = game
    now = time.time()
    admin = {"x-user": "admin"}
    data = {
        "title": "Treasure chest",
        "city": "london",
        "kind": "treasure",
        "x": 0,
        "z": 0,
        "starts_at": now - 10,
        "ends_at": now + 3600,
        "max_claims": 1,
    }
    assert c.post("/api/admin/collectibles", json=data).status_code == 403
    assert (
        c.post(
            "/api/admin/collectibles", json={**data, "x": 30, "z": 30}, headers=admin
        ).status_code
        == 422
    )
    item = c.post("/api/admin/collectibles", json=data, headers=admin).json()
    goal = {
        "title": "Find the chest",
        "city": "london",
        "requirements": {"treasure": 1},
        "credits": 10,
        "xp": 20,
    }
    assert (
        c.post(
            "/api/admin/missions", json={**goal, "requirements": {}}, headers=admin
        ).status_code
        == 422
    )
    assert c.post("/api/admin/missions", json=goal, headers=admin).status_code == 201
    with s.begin() as db:
        for name in ["owner", "member"]:
            db.add(Presence(user_id=name, city="london", x=0, z=0))
    path = "/api/collectibles/" + item["id"] + "/claim"
    assert c.post(path).status_code == 200
    assert c.post(path).json()["already_claimed"] is True
    assert c.post(path, headers={"x-user": "member"}).status_code == 409
    with s() as db:
        assert db.scalar(select(func.count()).select_from(MissionCompletion)) == 1
        assert (
            db.scalar(
                select(func.sum(Ledger.amount)).where(
                    Ledger.user_id == "owner", Ledger.currency == "credits"
                )
            )
            == 10
        )
    future = c.post(
        "/api/admin/collectibles", json={**data, "starts_at": now + 1800}, headers=admin
    ).json()
    assert c.post("/api/collectibles/" + future["id"] + "/claim").status_code == 409


def test_city_battle_uses_activity_city_time_window_and_suspension(game):
    c, s = game
    now = time.time()
    body = {
        "title": "Weekend city challenge",
        "cities": ["london", "birmingham"],
        "starts_at": now + 600,
        "ends_at": now + 3600,
    }
    assert c.post("/api/admin/city-battles", json=body).status_code == 403
    battle = c.post(
        "/api/admin/city-battles", json=body, headers={"x-user": "admin"}
    ).json()
    assert all(
        score["points"] == 0 for score in c.get("/api/city-battles").json()[0]["scores"]
    )
    with s.begin() as db:
        db.get(g.CityBattle, battle["id"]).starts_at = now - 100
        db.get(User, "owner").city = "birmingham"
        for key, created in [("counted", now - 50), ("old", now - 500)]:
            db.add(
                Collectible(id=key, city="london", title=key, kind="fruit", x=0, z=0)
            )
            db.flush()
            db.add(Claim(user_id="owner", collectible_id=key, created_at=created))
    scores = {
        x["city"]: x["points"] for x in c.get("/api/city-battles").json()[0]["scores"]
    }
    assert scores == {"london": 1, "birmingham": 0}
    with s.begin() as db:
        db.get(User, "owner").suspended = True
    assert all(x["points"] == 0 for x in c.get("/api/city-battles").json()[0]["scores"])


def test_blocked_owner_open_crew_is_hidden_and_cannot_be_joined(game):
    c, sessions = game
    with sessions.begin() as db:
        db.get(Crew, "private").private = False
        db.add(Social(actor="owner", target="outsider", kind="block"))
    assert c.get("/api/crews", headers={"x-user": "outsider"}).json() == []
    assert (
        c.post("/api/crews/private/join", headers={"x-user": "outsider"}).status_code
        == 404
    )
    with sessions() as db:
        assert db.get(CrewMember, ("private", "outsider")) is None


def test_suspended_peer_cannot_accept_or_receive_media_token(game):
    c, sessions = game
    from backend.api.models import MediaSession

    with sessions.begin() as db:
        db.add(
            MediaSession(
                id="pending-call", requester="owner", target="member", kind="voice"
            )
        )
        db.add(
            MediaSession(
                id="active-call",
                requester="owner",
                target="member",
                kind="voice",
                state="accepted",
                accepted_at=time.time(),
            )
        )
        db.get(User, "owner").suspended = True
    assert (
        c.post(
            "/api/media/pending-call/accept", headers={"x-user": "member"}
        ).status_code
        == 403
    )
    assert (
        c.post("/api/media/active-call/token", headers={"x-user": "member"}).status_code
        == 403
    )
