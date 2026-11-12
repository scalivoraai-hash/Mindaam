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

def test_probe_measures_sql_on_its_connection_and_removes_listeners(monkeypatch):
    import time
    from sqlalchemy import create_engine,event,text
    from sqlalchemy.orm import Session
    engine=create_engine('sqlite://')
    monkeypatch.setenv('APP_ENV','staging')
    with Session(engine) as db:
        with diagnostics.transaction_probe(db) as details:
            conn=db.connection()
            def latency(*args):time.sleep(.03)
            event.listen(conn,'before_cursor_execute',latency)
            db.execute(text('SELECT 1'))
            event.remove(conn,'before_cursor_execute',latency)
            db.commit()
        assert details['sql_count']==1
        assert details['sql_ms']>=30
        assert details['sql_max_ms']>=30
        assert details['thread_cpu_ms']>=0
        assert not list(conn.dispatch.before_cursor_execute)
        assert not list(conn.dispatch.after_cursor_execute)
    engine.dispose()

def test_probe_cleans_up_after_rollback(monkeypatch):
    import pytest
    from sqlalchemy import create_engine,text
    from sqlalchemy.orm import Session
    engine=create_engine('sqlite://')
    monkeypatch.setenv('APP_ENV','staging')
    with Session(engine) as db:
        with pytest.raises(RuntimeError):
            with diagnostics.transaction_probe(db):
                conn=db.connection();db.execute(text('SELECT 1'))
                raise RuntimeError('abort')
        db.rollback()
        assert not list(conn.dispatch.before_cursor_execute)
        assert not list(conn.dispatch.after_cursor_execute)
    engine.dispose()

def test_production_probe_does_not_acquire_connection(monkeypatch):
    monkeypatch.setenv('APP_ENV','production')
    with diagnostics.transaction_probe(object()) as details:assert details=={}

def test_timing_details_are_allowlisted_and_finite(monkeypatch,caplog):
    monkeypatch.setenv('APP_ENV','staging')
    monkeypatch.setattr(diagnostics,'_last_timing',0)
    monkeypatch.setattr(diagnostics,'time',SimpleNamespace(monotonic=lambda:101))
    diagnostics.timing(100,100,[],{'sql_ms':400,'sql_count':3,'sql_max_ms':float('inf'),'token':'private','connection_ms':-1})
    result=json.loads(caplog.records[-1].message.split(' ',1)[1])
    assert result['sql_ms']==400 and result['sql_count']==3
    assert 'sql_max_ms' not in result and 'token' not in result and 'connection_ms' not in result
