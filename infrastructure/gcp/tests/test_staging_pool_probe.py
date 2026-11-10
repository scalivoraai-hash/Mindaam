import json, os, sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Blocked
from staging_pool_probe import collect, QUERY, PROBE

class Cloud:
    project='mindaam';region='europe-west2'
    def __init__(self,fail=False,samples=60):self.calls=[];self.fail=fail;self.samples=samples;self.manifest=None
    def sa(self,env):return env+'@example.test'
    def gc(self,*args):
        self.calls.append(args)
        if args[:3]==('run','jobs','replace'):
            self.manifest=json.loads(Path(args[3]).read_text());return {}
        if args[:3]==('run','jobs','execute'):
            if self.fail:raise Blocked('Probe execution failed')
            return {'metadata':{'name':'probe-execution'}}
        if args[:2]==('logging','read'):
            return [{'textPayload':'MINDAAM_POOL_RESULT '+json.dumps({'read_only':True,'samples':[{'groups':[]}]*self.samples})}]
        if args[:3]==('run','jobs','delete'):return {}
        raise AssertionError(args)

class PoolProbe(unittest.TestCase):
    def release(self):return {'environment':'staging','image':'registry/app@sha256:'+'a'*64}
    @patch.dict(os.environ,{'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1'})
    def test_exact_image_staging_identity_and_cleanup(self):
        c=Cloud();result=collect(c,self.release())
        spec=c.manifest['spec']['template']['spec']['template']['spec']
        self.assertEqual(spec['serviceAccountName'],'staging@example.test')
        self.assertEqual(spec['containers'][0]['image'],self.release()['image'])
        self.assertEqual(spec['containers'][0]['env'],[{'name':'DATABASE_URL','valueFrom':{'secretKeyRef':{'name':'mindaam-staging-database-url','key':'latest'}}}])
        self.assertEqual(c.calls[-1][:4],('run','jobs','delete','mindaam-pool-probe-123-1'))
        self.assertEqual(len(result['samples']),60)
        self.assertIn('default_transaction_read_only=on',PROBE)
        self.assertIn('statement_timeout=2000',PROBE)
        self.assertIn("('mindaam_staging','mindaam_staging')",PROBE)
        self.assertNotIn('query,',QUERY)
        self.assertNotIn('query ',QUERY)
        self.assertIn('count(*)',QUERY)
    @patch.dict(os.environ,{'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1'})
    def test_failed_or_incomplete_probe_always_deletes_only_its_job(self):
        for c in (Cloud(fail=True),Cloud(samples=2)):
            with self.assertRaises(Blocked):collect(c,self.release())
            self.assertEqual(c.calls[-1][:4],('run','jobs','delete','mindaam-pool-probe-123-1'))
    @patch.dict(os.environ,{'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1'})
    def test_production_is_refused_before_any_cloud_action(self):
        c=Cloud()
        with self.assertRaises(Blocked):collect(c,{**self.release(),'environment':'production'})
        self.assertEqual(c.calls,[])
