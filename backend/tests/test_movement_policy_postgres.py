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
