import json
from types import SimpleNamespace
from backend.api import motion_diagnostics as diagnostics

def test_slow_staging_timings_are_bounded_and_contain_only_durations(monkeypatch,caplog):
    monkeypatch.setenv('APP_ENV','staging')
    monkeypatch.setattr(diagnostics,'_last_timing',0)
    monkeypatch.setattr(diagnostics,'time',SimpleNamespace(monotonic=lambda:101))
    phases=[('authentication',100.2),('context',100.3),('simulation',100.4)]
    diagnostics.timing(100,99.9,phases)
    diagnostics.timing(100,99.9,phases)
    records=[r.message for r in caplog.records if r.message.startswith('movement_transaction_timing ')]
    assert len(records)==1
    assert json.loads(records[0].split(' ',1)[1])==dict(authentication_ms=200,context_ms=100,simulation_ms=100,commit_and_publish_ms=600,queue_ms=100)

def test_production_does_not_emit_staging_timings(monkeypatch,caplog):
    monkeypatch.setenv('APP_ENV','production')
    diagnostics.timing(0,0,[])
    assert not caplog.records
