import contextlib, io, json, os, sys, types, unittest
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
    def test_runtime_probe_is_bounded_read_only_and_records_wait_timings(self):
        queries=[]
        class Connection:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def execute(self,sql):
                queries.append(sql)
                if sql=='SELECT current_database(),current_user':self.rows=[('mindaam_staging','mindaam_staging')]
                elif sql=='SHOW default_transaction_read_only':self.rows=[('on',)]
                elif 'FROM pg_settings' in sql:self.rows=[('synchronous_commit','on'),('track_wal_io_timing','off')]
                elif 'FROM pg_stat_wal' in sql:self.rows=[(1.,2.,3.,4.,0.,0.)]
                elif sql==QUERY:self.rows=[('active','IO','WALSync',2,.4,.2)]
                else:raise AssertionError('Unexpected SQL in read-only probe')
                return self
            def fetchone(self):return self.rows[0]
            def fetchall(self):return self.rows
        def connect(**args):
            self.assertTrue(args['autocommit'])
            self.assertIn('default_transaction_read_only=on',args['options'])
            return Connection()
        driver=types.ModuleType('psycopg');driver.connect=connect
        conninfo=types.ModuleType('psycopg.conninfo');conninfo.conninfo_to_dict=lambda _:{}
        output=io.StringIO()
        with patch.dict(sys.modules,{'psycopg':driver,'psycopg.conninfo':conninfo}),patch.dict(os.environ,{'DATABASE_URL':'postgresql://private'}),patch('time.sleep') as sleep,contextlib.redirect_stdout(output):
            exec('QUERY='+repr(QUERY)+'\n'+PROBE,{})
        result=json.loads(output.getvalue().split('MINDAAM_POOL_RESULT ')[1])
        self.assertEqual(len(result['samples']),60)
        self.assertEqual(sleep.call_count,59)
        self.assertEqual(queries.count(QUERY),60)
        self.assertGreaterEqual(result['connection_ms'],0)
        self.assertTrue(all(s['query_ms']>=0 for s in result['samples']))
        self.assertEqual(result['samples'][0]['groups'][0]['wait'],'WALSync')
        self.assertEqual(result['settings']['track_wal_io_timing'],'off')
        self.assertEqual(result['wal_fields'],['records','bytes','writes','syncs','write_ms','sync_ms'])
        self.assertNotIn('private',output.getvalue())

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
