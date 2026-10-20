import pytest
from fastapi import FastAPI, Depends, Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from backend.api import discovery as d
from backend.api.expansion import seed_catalog
from backend.api.models import User, Social


@pytest.fixture
def discovery(tmp_path):
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "discovery.db"),
        connect_args={"check_same_thread": False},
    )
    d.Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions.begin() as db:
        seed_catalog(db)
        for name, privacy in [
            ("viewer", "City Mode"),
            ("public_person", "City Mode"),
            ("ghost_person", "Ghost Mode"),
            ("friend_person", "Friends Only"),
            ("blocked_person", "City Mode"),
        ]:
            db.add(
                User(
                    id=name,
                    username=name,
                    email=name + "@example.test",
                    password_hash="unused",
                    privacy=privacy,
                    onboarded=True,
                )
            )
        db.flush()
        db.add(Social(actor="blocked_person", target="viewer", kind="block"))

    def dep():
        with sessions() as db:
            try:
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def auth(x_user: str = Header(default="viewer"), db=Depends(d.get_db)):
        return db.get(User, x_user)

    app = FastAPI()
    app.include_router(d.router)
    app.dependency_overrides[d.get_db] = dep
    app.dependency_overrides[d.current_user] = auth
    with TestClient(app, client=("qa-"+tmp_path.name, 50000)) as client:
        yield client, sessions
    engine.dispose()


def test_waitlist_counts_are_unique_reversible_and_not_fabricated(discovery):
    client, sessions = discovery
    assert all(c["interested_count"] == 0 for c in client.get("/api/cities").json())
    for _ in range(3):
        response = client.post("/api/cities/glasgow/interest")
        assert response.status_code == 200
        assert response.json()["interested_count"] == 1
    assert client.get("/api/cities/interests").json() == ["glasgow"]
    assert client.post("/api/cities/london/interest").status_code == 422
    assert client.post("/api/cities/invented/interest").status_code == 422
    assert client.delete("/api/cities/glasgow/interest").status_code == 200
    assert client.get("/api/cities/interests").json() == []


def test_search_respects_blocks_ghost_and_friends_and_excludes_private_fields(
    discovery,
):
    client, sessions = discovery
    result = client.get("/api/people/search?q=person").json()
    assert [p["id"] for p in result] == ["public_person"]
    assert set(result[0]) == {"id", "username", "avatar"}
    with sessions.begin() as db:
        db.add(Social(actor="viewer", target="friend_person", kind="friend"))
    assert {p["id"] for p in client.get("/api/people/search?q=person").json()} == {
        "public_person",
        "friend_person",
    }
    assert client.get("/api/people/search?q=%20%20").status_code == 422
    assert client.get("/api/people/search?q=%25%25").json() == []


def test_passport_is_private_server_earned_idempotent(discovery):
    client, sessions = discovery
    assert client.get("/api/passport").json()["stamps"] == []
    with sessions.begin() as db:
        d.record_stamp(db, "viewer", "london")
        d.record_stamp(db, "viewer", "london")
    own = client.get("/api/passport").json()
    assert own["kind"] == "virtual_city_passport"
    assert len(own["stamps"]) == 1
    assert (
        client.get("/api/passport", headers={"x-user": "public_person"}).json()[
            "stamps"
        ]
        == []
    )
    assert client.post("/api/passport", json={"city": "london"}).status_code == 405


def test_provider_discloses_actual_adapter(discovery):
    client, _ = discovery
    result = client.get("/api/world-provider").json()
    assert result["simulated"] is True
    assert result["photorealistic"] is False


def test_catalog_has_bounded_queries_and_reads_current_thresholds(discovery):
    from sqlalchemy import event
    from backend.api.expansion import Destination
    from backend.api.models import Config
    _, sessions = discovery
    with sessions.begin() as db:
        db.get(Destination, 'london').threshold = 123
    engine = sessions.kw['bind']
    statements = []
    def record(conn, cursor, statement, parameters, context, many):
        statements.append(statement)
    event.listen(engine, 'before_cursor_execute', record)
    try:
        with sessions() as db:
            rows = d.catalog(db)
        assert len(rows) > 100
        assert len(statements) <= 2
        assert next(r for r in rows if r['id'] == 'london')['interest_threshold'] == 123
        with sessions.begin() as db:
            db.get(Config, 'city_demand').value = {'threshold': 7000}
        with sessions() as db:
            updated = d.catalog(db)
        assert next(r for r in updated if r['id'] == 'london')['interest_threshold'] == 123
        assert next(r for r in updated if r['id'] == 'glasgow')['interest_threshold'] == 7000
    finally:
        event.remove(engine, 'before_cursor_execute', record)
