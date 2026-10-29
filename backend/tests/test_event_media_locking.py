"""Real PostgreSQL reproduction of event cleanup versus conversation polling."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event as Signal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from backend.api import conversations, events, gifts
from backend.api.models import User, Event, MediaSession, Attendee, ConversationMember


def test_event_lock_precedes_session_lock():
    statements=[]
    class DB:
        def scalar(self, statement):
            statements.append(statement)
            return 'event-id' if len(statements)==1 else None
    conversations.locked_session(DB(),'session-id')
    assert statements[0]._for_update_arg is None
    assert statements[1].column_descriptions[0]['entity'] is Event
    assert statements[1]._for_update_arg is not None
    assert statements[2].column_descriptions[0]['entity'] is MediaSession
    assert statements[2]._for_update_arg is not None


@pytest.mark.skipif(not os.getenv('DATABASE_URL','').startswith('postgresql'),reason='Real PostgreSQL service supplied by the backend CI job')
def test_event_cleanup_and_social_poll_do_not_deadlock():
    from backend.api.db import Base, engine, APP_ENV
    assert APP_ENV=='test', 'Never create concurrency fixtures in a deployed database'
    schema='lock_regression_'+uuid4().hex
    scoped=engine.execution_options(schema_translate_map={None:schema})
    with engine.begin() as conn:conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    pool=ThreadPoolExecutor(max_workers=1)
    started=Signal();worker_pid=[];future=None
    try:
        Base.metadata.create_all(scoped)
        with Session(scoped) as db, db.begin():
            u=User(id='lock-user',email='locks@example.test',username='lock-test',password_hash='not-a-login')
            db.add(u);db.flush()
            e=Event(id='lock-event',host_id=u.id,title='Concurrency fixture',city='london',starts_at=time.time(),status='live',communication_mode='voice',session_id='lock-media')
            db.add(e);db.flush()
            db.add(MediaSession(id='lock-media',requester=u.id,target=u.id,kind='voice',state='accepted',event_id=e.id,accepted_at=time.time()))
            db.flush()
            db.add_all([Attendee(event_id=e.id,user_id=u.id,role='host'),ConversationMember(session_id='lock-media',user_id=u.id)])
        def poll():
            with Session(scoped) as db, db.begin():
                worker_pid.append(db.scalar(text('SELECT pg_backend_pid()')))
                u=db.get(User,'lock-user');started.set()
                try:gifts.activity('conversation','lock-media',u,db)
                except HTTPException as exc:
                    # Once cleanup commits, the ended conversation must be denied.
                    assert exc.status_code in (403,409)
                    return 'ended-denied'
                return 'active'
        with Session(scoped) as db:
            try:
                e=db.scalar(select(Event).where(Event.id=='lock-event').with_for_update())
                future=pool.submit(poll)
                assert started.wait(2)
                # Wait for the actual database lock wait, not an assumed thread delay.
                deadline=time.monotonic()+2
                with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as observer:
                    while time.monotonic()<deadline:
                        wait=observer.scalar(text('SELECT wait_event_type FROM pg_stat_activity WHERE pid=:pid'),{'pid':worker_pid[0]})
                        if wait=='Lock':break
                        time.sleep(.01)
                    else:pytest.fail('Social poll did not reach the concurrent lock boundary')
                events.finish(db,e,'ended')
                db.commit()
            finally:db.rollback()
        assert future.result(timeout=5)=='ended-denied'
        with Session(scoped) as db:
            assert db.get(Event,'lock-event').status=='ended'
            assert db.get(MediaSession,'lock-media').state=='ended'
            assert db.get(ConversationMember,('lock-media','lock-user')).state=='left'
    finally:
        pool.shutdown(wait=True)
        with engine.begin() as conn:conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
