from fastapi.testclient import TestClient
from backend.api import main

def test_database_outage_fails_readiness_but_not_process_liveness(monkeypatch):
 def unavailable():raise RuntimeError('database temporarily unavailable')
 monkeypatch.setattr(main.engine,'connect',unavailable)
 client=TestClient(main.app,raise_server_exceptions=False)
 assert client.get('/api/live').status_code==200
 assert client.get('/api/health').status_code==503
 assert client.get('/ready').status_code==503
