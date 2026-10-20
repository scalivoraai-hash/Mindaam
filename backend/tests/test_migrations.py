"""Actual migration application and database-level ledger immutability."""
import os
import subprocess
import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.api.models import User
from backend.api.economy import credit

def test_clean_migration_and_immutable_ledger(tmp_path):
    root=Path(__file__).resolve().parents[2]
    url='sqlite:///'+str(tmp_path/'migrations.db')
    result=subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],cwd=root,env={**os.environ,'DATABASE_URL':url,'APP_ENV':'test'},capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    engine=create_engine(url)
    with Session(engine) as db:
        u=User(id='migration-test',email='migration@example.test',username='migration',password_hash='test-only-no-login')
        db.add(u);db.flush();credit(db,u.id,20,'test','test','test');db.commit()
    for sql in ["UPDATE wallet_transactions SET amount=999","DELETE FROM wallet_transactions"]:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:connection.execute(text(sql))
    with engine.connect() as connection:assert connection.scalar(text('SELECT SUM(amount) FROM wallet_transactions'))==20
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO businesses (id,owner_id,name,city,address,latitude,longitude,status,funds,signage) VALUES ('negative',NULL,'Test','london','',0,0,'listed',-1,'{}')"))
    engine.dispose()
