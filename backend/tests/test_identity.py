import hashlib
import json
import re
import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from backend.api import identity as i
from backend.api.models import User, Session as AuthSession
from backend.api.auth import check_password


@pytest.fixture
def identity(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("MAIL_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("LOCAL_MAIL_DIR", str(tmp_path / "mail"))
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "identity.db"),
        connect_args={"check_same_thread": False},
    )
    i.Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(i, "SessionLocal", sessions)
    with sessions.begin() as db:
        db.add(
            User(
                id="player",
                email="player@example.test",
                username="player",
                password_hash="unused",
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

    app = FastAPI()
    app.include_router(i.router)
    app.dependency_overrides[i.get_db] = dep
    with TestClient(app, client=("qa-"+tmp_path.name, 50000)) as client:
        yield client, sessions, tmp_path
    engine.dispose()


def raw_token(sessions):
    with sessions() as db:
        return (
            json.loads(db.scalar(select(i.MailOutbox)).payload)["body"]
            .split("#token=")[1]
            .split()[0]
        )


def test_verification_hash_single_use_and_no_api_token(identity):
    client, sessions, _ = identity
    known = client.post(
        "/api/auth/request-verification", json={"email": "player@example.test"}
    )
    unknown = client.post(
        "/api/auth/request-verification", json={"email": "absent@example.test"}
    )
    assert known.status_code == 202 and known.json() == unknown.json()
    token = raw_token(sessions)
    assert token not in known.text
    with sessions() as db:
        assert db.get(i.IdentityToken, hashlib.sha256(token.encode()).hexdigest())
    assert (
        client.post("/api/auth/verify-email", json={"token": token}).status_code == 200
    )
    assert (
        client.post("/api/auth/verify-email", json={"token": token}).status_code == 400
    )
    with sessions() as db:
        assert db.get(User, "player").verified


def test_reset_revokes_sessions_and_expired_link_fails(identity):
    client, sessions, _ = identity
    with sessions.begin() as db:
        db.add(
            AuthSession(
                id="sessionhash", user_id="player", expires_at=time.time() + 3600
            )
        )
    client.post("/api/auth/forgot-password", json={"email": "player@example.test"})
    token = raw_token(sessions)
    assert (
        client.post("/api/auth/verify-email", json={"token": token}).status_code == 400
    )
    r = client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": "Strong test password 123"},
    )
    assert r.status_code == 200, r.text
    with sessions() as db:
        assert db.get(AuthSession, "sessionhash") is None
        assert check_password(
            "Strong test password 123", db.get(User, "player").password_hash
        )
    assert (
        client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "Another password 123"},
        ).status_code
        == 400
    )


def test_outbox_committed_local_delivery_scrubs_payload(identity):
    client, sessions, path = identity
    client.post("/api/auth/forgot-password", json={"email": "player@example.test"})
    assert i.drain_outbox() == {"sent": 1, "failed": 0}
    assert len(list((path / "mail").glob("*.eml"))) == 1
    with sessions() as db:
        assert db.scalar(select(i.MailOutbox)).payload == ""
    assert i.drain_outbox() == {"sent": 0, "failed": 0}


def test_production_email_configuration_fails_closed(identity, monkeypatch):
    client, _, _ = identity
    monkeypatch.setenv("APP_ENV", "production")
    assert (
        client.post(
            "/api/auth/forgot-password", json={"email": "player@example.test"}
        ).status_code
        == 503
    )


def test_expiry_and_resend_throttle(identity):
    client, sessions, _ = identity
    for _ in range(3):
        client.post(
            "/api/auth/request-verification", json={"email": "player@example.test"}
        )
    token = raw_token(sessions)
    with sessions.begin() as db:
        rows = list(db.scalars(select(i.IdentityToken)))
        assert len(rows) == 1
        rows[0].expires_at = time.time() - 1
    assert (
        client.post("/api/auth/verify-email", json={"token": token}).status_code == 400
    )
