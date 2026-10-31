import json,sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ledger_review import run,probe_source
from common import Blocked

class LedgerReviewTests(unittest.TestCase):
 def test_probe_uses_runtime_identity_and_read_only_transaction(self):
  source=probe_source();compile(source,'ledger-probe','exec')
  self.assertIn("os.environ['RUNTIME_DATABASE_URL']",source)
  self.assertIn('SET TRANSACTION READ ONLY',source)
  self.assertIn("result.pop('accounts')",source)
  self.assertNotIn('bootstrap_owner',source)
 def test_existing_job_execution_only_and_aggregate_evidence(self):
  class Cloud:
   project='mindaam';region='europe-west2'
   def __init__(self):self.calls=[];self.saved=None
   def get_json(self,key):return {'sha':'a'*40,'image':'image@sha256:test','revision':'revision'}
   def sa(self,kind):return kind+'@example.test'
   def owned(self,*args):pass
   def gc(self,*args):
    self.calls.append(args)
    if args[:3]==('run','jobs','describe'):return {'metadata':{},'spec':{'template':{'spec':{'template':{'spec':{'serviceAccountName':self.sa('migrate'),'containers':[{'image':'image@sha256:test'}]}}}}}}
    if args[:3]==('run','jobs','execute'):return {'metadata':{'name':'execution'}}
    if args[:2]==('logging','read'):return [{'textPayload':'MINDAAM_LEDGER_DRY_RUN '+json.dumps({'mode':'DRY_RUN_ONLY','adjustments_applied':False,'database_identity_verified':True,'totals':{}})}]
    raise AssertionError(args)
   def put_json(self,key,value):self.saved=value
  c=Cloud();service={'status':{'latestReadyRevisionName':'revision'},'spec':{'template':{'spec':{'containers':[{'image':'image@sha256:test'}]}}}}
  import os
  old=os.getcwd()
  try:
   with TemporaryDirectory() as directory,patch('ledger_review.ready_service',return_value=service):
    os.chdir(directory);run(c,'a'*40)
   self.assertFalse(c.saved['adjustments_applied'])
   self.assertEqual(len([x for x in c.calls if x[:3]==('run','jobs','execute')]),1)
   self.assertFalse(any('deploy' in x or 'replace' in x or 'delete' in x for x in c.calls))
  finally:os.chdir(old)
