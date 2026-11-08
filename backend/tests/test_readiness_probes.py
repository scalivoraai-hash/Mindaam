"""Readiness stays fail-closed without loading PostGIS in pooled sessions."""
import logging
import pytest
from fastapi import HTTPException
from backend.api import main


class Database:
    def __init__(self, version="3.4", failure=None):
        self.version, self.failure, self.statements = version, failure, []
    def connect(self): return self
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def execute(self, query):
        self.statements.append(str(query))
        if self.failure: raise self.failure
        return self
    def scalar_one_or_none(self): return self.version


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_readiness_checks_required_schema_and_extension_catalogue(monkeypatch, environment):
    db = Database()
    monkeypatch.setattr(main, "engine", db)
    monkeypatch.setattr(main, "APP_ENV", environment)
    monkeypatch.setattr(main, "redis_client", None)
    result = main.ready()
    assert result == {"status": "ready", "environment": environment, "release_ready": False}
    assert db.statements == [
        "SELECT 1 FROM users LIMIT 1",
        "SELECT extversion FROM pg_catalog.pg_extension WHERE extname = 'postgis'",
    ]


@pytest.mark.parametrize("failure", ["schema", "extension", "redis"])
def test_dependencies_fail_closed_without_logging_private_details(monkeypatch, caplog, failure):
    secret = "private-host password=never-export-this"
    db = Database(version=None if failure == "extension" else "3.4",
                  failure=RuntimeError(secret) if failure == "schema" else None)
    class Redis:
        def ping(self):
            if failure == "redis": raise RuntimeError(secret)
    monkeypatch.setattr(main, "engine", db)
    monkeypatch.setattr(main, "APP_ENV", "staging")
    monkeypatch.setattr(main, "redis_client", Redis())
    with caplog.at_level(logging.WARNING, logger="pulseworld.readiness"):
        with pytest.raises(HTTPException) as error:
            main.ready()
    assert error.value.status_code == 503
    expected = {"schema": "database", "extension": "postgis_catalogue", "redis": "redis"}[failure]
    assert "dependency=" + expected in caplog.text
    assert "never-export-this" not in caplog.text
    assert "private-host" not in caplog.text

