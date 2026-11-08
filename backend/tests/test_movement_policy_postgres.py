"""Exercise competing settings writers on the existing isolated CI database."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import pytest
from fastapi import HTTPException
from sqlalchemy import text, select, func
from sqlalchemy.orm import Session
from backend.api.models import Config, Audit, User
from backend.api.movement_policy import save, DEFAULTS, KEY

@pytest.mark.skipif(not os.getenv('DATABASE_URL','').startswith('postgresql'),reason='Requires the existing backend CI PostgreSQL service')
def test_concurrent_initial_save_has_one_winner_and_one_audit_record():
 from backend.api.db import Base, engine, APP_ENV
 assert APP_ENV=='test'
 schema='movement_settings_'+uuid4().hex
 scoped=engine.execution_options(schema_translate_map={None:schema})
 with engine.begin() as db:db.execute(text(f'CREATE SCHEMA "{schema}"'))
 try:
  Base.metadata.create_all(scoped)
  with Session(scoped) as db,db.begin():
   db.add(User(id='owner',email='owner@example.test',username='localowner',password_hash='not-a-login',role='super_admin'))
  barrier=Barrier(2)
  def write(speed):
   try:
    with Session(scoped) as db,db.begin():
     db.execute(text("SET LOCAL lock_timeout='5s'"))
     owner=db.get(User,'owner');barrier.wait(timeout=5)
     save(db,owner,{**DEFAULTS,'walk':speed},0,'Concurrent local settings test')
    return 200
   except HTTPException as error:return error.status_code
  with ThreadPoolExecutor(max_workers=2) as pool:
   results=list(pool.map(write,[1.25,1.5]))
  assert sorted(results)==[200,409]
  with Session(scoped) as db:
   assert db.get(Config,KEY).value['version']==1
   assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action=='movement.settings_updated'))==1
 finally:
  with engine.begin() as db:db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


@pytest.mark.skipif(not os.getenv('DATABASE_URL','').startswith('postgresql'),reason='Requires the existing backend CI PostgreSQL service')
def test_snapshot_render_does_not_block_authenticated_movement(monkeypatch):
 import time
 from threading import Event
 from sqlalchemy.orm import sessionmaker
 from backend.api import main,commerce
 from backend.api.auth import session_token
 from backend.api.db import Base,engine,APP_ENV
 from backend.api.expansion import seed_catalog
 from backend.api.growth import WorldAccess
 from backend.api.models import Presence
 assert APP_ENV=='test'
 schema='snapshot_contention_'+uuid4().hex
 scoped=engine.execution_options(schema_translate_map={None:schema})
 sessions=sessionmaker(scoped,expire_on_commit=False)
 with engine.begin() as db:db.execute(text(f'CREATE SCHEMA "{schema}"'))
 rendered,release=Event(),Event()
 original=commerce.world_businesses
 def slow_render(*args):
  rendered.set()
  assert release.wait(5)
  return original(*args)
 try:
  Base.metadata.create_all(scoped)
  with sessions.begin() as db:
   seed_catalog(db)
   u=User(id='walker',email='walker@example.test',username='walker',password_hash='test-only',onboarded=True)
   db.add(u);db.flush();token=session_token(db,u)
   db.add(WorldAccess(user_id=u.id,destination_id='london',source='starter'))
   db.add(Presence(user_id=u.id,city='london',zone_id='world',x=0,z=0,last_move=time.time()-.2))
  monkeypatch.setattr(main,'SessionLocal',sessions)
  monkeypatch.setattr(commerce,'world_businesses',slow_render)
  with ThreadPoolExecutor(max_workers=2) as pool:
   snapshot=pool.submit(main.realtime_state,token)
   try:
    assert rendered.wait(5)
    move=main.MotionInput(type='input',seq=1,city='london',zone='world',action='move',x=1,z=0)
    result=pool.submit(main.realtime_motion,token,move).result(timeout=1)
    assert result is not None and result['position']['x']>0
    stop=main.realtime_motion(token,move.model_copy(update={'seq':2,'x':0}))
    assert stop['position']['speed']==0
   finally:release.set()
   snapshot.result(timeout=5)
  with sessions() as db:
   assert db.get(Presence,'walker').x==stop['position']['x']
 finally:
  release.set()
  with engine.begin() as db:db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


@pytest.mark.skipif(not os.getenv('DATABASE_URL','').startswith('postgresql'),reason='Requires the existing backend CI PostgreSQL service')
def test_realtime_input_with_a_concurrent_player_lock(monkeypatch):
 import time
 from sqlalchemy.orm import sessionmaker
 from backend.api import main
 from backend.api.auth import session_token
 from backend.api.db import Base,engine,APP_ENV
 from backend.api.expansion import seed_catalog
 from backend.api.growth import WorldAccess
 from backend.api.models import Presence
 assert APP_ENV=='test'
 schema='motion_contention_'+uuid4().hex
 scoped=engine.execution_options(schema_translate_map={None:schema})
 sessions=sessionmaker(scoped,expire_on_commit=False)
 with engine.begin() as db:db.execute(text(f'CREATE SCHEMA "{schema}"'))
 try:
  Base.metadata.create_all(scoped)
  with sessions.begin() as db:
   seed_catalog(db)
   u=User(id='walker',email='walker@example.test',username='walker',password_hash='test-only',onboarded=True)
   db.add(u);db.flush();token=session_token(db,u)
   db.add(WorldAccess(user_id=u.id,destination_id='london',source='starter'))
   db.add(Presence(user_id=u.id,city='london',zone_id='world',x=0,z=0,last_move=time.time()-.2))
  monkeypatch.setattr(main,'SessionLocal',sessions)
  move=main.MotionInput(type='input',seq=1,city='london',zone='world',action='move',x=1,z=0)
  with sessions.begin() as blocker:
   blocker.scalar(select(User.id).where(User.id=='walker').with_for_update())
   assert main.realtime_motion(token,move) is None
   assert blocker.get(Presence,'walker').x==0
  fresh=move.model_copy(update={'seq':2})
  result=main.realtime_motion(token,fresh)
  assert result['seq']==2 and result['position']['x']>0
 finally:
  with engine.begin() as db:db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
