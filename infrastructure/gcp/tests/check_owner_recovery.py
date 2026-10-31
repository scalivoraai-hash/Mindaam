"""Exercise recovery issuance and the real existing reset handler on disposable SQL."""
import hashlib
import os
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from owner_recover import ISSUE, verified_owner
from common import Blocked
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from backend.api.identity import Base,IdentityToken,ResetInput,reset
from backend.api.models import User,Audit,Session as AuthSession
from backend.api.auth import check_password
scope={};exec(ISSUE,scope);issue=scope['issue']

class Recovery(unittest.TestCase):
 def setUp(self):
  self.engine=create_engine('sqlite://')
  Base.metadata.create_all(self.engine)
  self.sessions=sessionmaker(self.engine)
  with self.sessions.begin() as db:
   db.add(User(id='owner',email='sain@scalivora.com',username='mindaam_owner',role='super_admin',verified=True,password_hash='old'))
 def tearDown(self):self.engine.dispose()
 def test_verified_google_identity_required(self):
  for value in ({},{'email':'other@example.test','verified_email':True},{'email':'sain@scalivora.com','verified_email':False}):
   with self.assertRaises(Blocked):verified_owner(value)
  verified_owner({'email':'sain@scalivora.com','verified_email':True})
 def test_real_single_use_reset_preserves_role_and_revokes_sessions(self):
  with self.sessions.begin() as db:
   db.add(AuthSession(id='old-session',user_id='owner',expires_at=9999999999))
   token=issue(db,'sain@scalivora.com')
   self.assertEqual(db.get(User,'owner').password_hash,'old')
   self.assertIsNotNone(db.get(IdentityToken,hashlib.sha256(token.encode()).hexdigest()))
  with self.sessions.begin() as db:
   reset(ResetInput(token=token,password='Unique-local-regression-only-7!'),db)
   owner=db.get(User,'owner')
   self.assertEqual(owner.role,'super_admin')
   self.assertTrue(check_password('Unique-local-regression-only-7!',owner.password_hash))
   self.assertIsNone(db.get(AuthSession,'old-session'))
   self.assertEqual(set(db.scalars(select(Audit.action))),{'owner.recovery_issued','identity.password_reset'})
  with self.sessions.begin() as db:
   with self.assertRaises(Exception):reset(ResetInput(token=token,password='Another-local-only-8!'),db)
 def test_wrong_identity_duplicate_owner_and_rate_limit_fail_closed(self):
  with self.sessions.begin() as db:
   with self.assertRaises(ValueError):issue(db,'other@example.test')
   issue(db,'sain@scalivora.com')
   with self.assertRaises(ValueError):issue(db,'sain@scalivora.com')
  with self.sessions.begin() as db:
   db.add(User(id='second',email='second@example.test',username='second',role='super_admin',verified=True,password_hash='old'));db.flush()
   with self.assertRaises(ValueError):issue(db,'sain@scalivora.com')
 def test_expired_reset_rejected(self):
  with self.sessions.begin() as db:
   token=issue(db,'sain@scalivora.com')
   db.get(IdentityToken,hashlib.sha256(token.encode()).hexdigest()).expires_at=1
  with self.sessions.begin() as db:
   with self.assertRaises(Exception):reset(ResetInput(token=token,password='Another-local-only-8!'),db)
   self.assertEqual(db.get(User,'owner').password_hash,'old')

if __name__=='__main__':unittest.main()
