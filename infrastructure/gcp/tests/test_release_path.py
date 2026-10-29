"""Controlled release-path tests: no provider or application deployment."""
import copy
import datetime
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import ssl
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Cloud, Blocked, HERE
import readiness
import evidence
import review
import workflow
import deploy
import finalize
import vm_agent
from render import caddy_config, service

SHA = 'f53898771471b96debf3a91b65fa0de015152982'
IMAGE = 'europe-west2-docker.pkg.dev/mindaam/mindaam/app@sha256:' + 'a'*64
ORIGIN = 'https://mindaam-staging-qfrofqn4pq-nw.a.run.app'
RELEASE = {'sha': SHA, 'image': IMAGE, 'revision': 'staging-00001', 'environment': 'staging', 'origin': ORIGIN, 'provider_origin': ORIGIN}


def ready(c, env, revision):
    r = service(c, env, IMAGE, ORIGIN if env=='staging' else 'https://mindaam.com')
    r['metadata']['generation'] = 2
    r['status'] = {'observedGeneration': 2, 'latestReadyRevisionName': revision, 'latestCreatedRevisionName': revision,
                   'url': ORIGIN if env=='staging' else 'https://mindaam-production-123.run.app',
                   'conditions':[{'type':'Ready','status':'True'}]}
    return r


class ReleasePath(unittest.TestCase):
    def test_public_iam_delay_retries_but_bad_auth_and_content_fail(self):
        with patch('readiness.urlopen', side_effect=[HTTPError(ORIGIN,403,'Forbidden',{},None),
                   HTTPError(ORIGIN,503,'Unavailable',{},None), io.BytesIO(b'{"status":"ready"}')]) as get, patch('readiness.time.sleep'):
            self.assertEqual(readiness.read_url(ORIGIN,json_body=True), {'status':'ready'})
            self.assertEqual(get.call_count,3)
        for error in [HTTPError(ORIGIN,401,'Unauthorized',{},None), io.BytesIO(b'bad-json')]:
            with patch('readiness.urlopen', side_effect=error if isinstance(error,Exception) else None,
                       return_value=error), patch('readiness.time.sleep') as sleep:
                with self.assertRaises(Blocked): readiness.read_url(ORIGIN,json_body=True)
                sleep.assert_not_called()
        with patch('readiness.urlopen', side_effect=HTTPError(ORIGIN,403,'Forbidden',{},None)):
            with self.assertRaisesRegex(Blocked,'deadline'): readiness.read_url(ORIGIN,timeout=0)

    def test_tls_propagation_bounded_and_verification_preserved(self):
        from unittest.mock import MagicMock
        raw = MagicMock(); tls = MagicMock()
        with patch('readiness.socket.create_connection', side_effect=[OSError('DNS pending'), raw]), \
             patch('readiness.ssl.create_default_context') as context, patch('readiness.time.sleep') as sleep:
            context.return_value.wrap_socket.return_value.__enter__.return_value = tls
            readiness.ready_tls('turn.mindaam.com')
            sleep.assert_called_once()
            self.assertEqual(context.return_value.wrap_socket.call_args.kwargs['server_hostname'], 'turn.mindaam.com')
            tls.getpeercert.assert_called_once()
        with patch('readiness.socket.create_connection', side_effect=ssl.SSLError('bad certificate')):
            with self.assertRaisesRegex(Blocked, 'TLS readiness deadline'):
                readiness.ready_tls('turn.mindaam.com', timeout=0)

    def test_revision_observed_generation_and_failure(self):
        c=Cloud('mindaam'); final=ready(c,'staging','staging-00001'); pending=copy.deepcopy(final)
        pending['status']['observedGeneration']=1
        with patch.object(c,'gc',side_effect=[pending,final]), patch('readiness.time.sleep') as sleep:
            self.assertEqual(readiness.ready_service(c,'mindaam-staging'),final);sleep.assert_called_once()
        pending['status']['conditions']=[{'type':'Ready','status':'False','reason':'ContainerMissing'}]
        with patch.object(c,'gc',return_value=pending):
            with self.assertRaisesRegex(Blocked,'ContainerMissing'):readiness.ready_service(c,'mindaam-staging')

    def test_metric_delay_scopes_and_fail_closed(self):
        c=Cloud('mindaam'); calls={}; filters=[]
        def response(req,**kw):
            q=parse_qs(urlsplit(req.full_url).query);f=q['filter'][0];filters.append(f)
            calls[f]=calls.get(f,0)+1
            return io.StringIO(json.dumps({} if calls[f]==1 else {'timeSeries':[{'points':[{'value':{'doubleValue':.2}}]}]}))
        with patch('evidence.command',return_value='not-a-real-token'), patch.object(c,'gc',return_value={'id':'123','labels':{'application':'mindaam'}}), \
             patch('evidence.urlopen',side_effect=response), patch('evidence.time.sleep') as sleep:
            result=evidence.metrics(c,RELEASE);self.assertEqual(len(result['series']),10);sleep.assert_called_once()
        self.assertTrue(any('revision_name = "staging-00001"' in f for f in filters))
        self.assertTrue(any('database_id = "mindaam:mindaam-postgres"' in f for f in filters))
        self.assertTrue(any('instance_id = "123"' in f for f in filters))
        with patch('evidence.command',return_value='test'), patch.object(c,'gc',return_value={'id':'123','labels':{'application':'mindaam'}}), \
             patch('evidence.urlopen',side_effect=lambda *a,**k:io.StringIO('{}')):
            with self.assertRaisesRegex(Blocked,'host_memory'):evidence.metrics(c,RELEASE,timeout=0)
        with patch('evidence.command',return_value='test'), patch.object(c,'gc',return_value={'id':'123','labels':{'application':'mindaam'}}), \
             patch('evidence.urlopen',side_effect=HTTPError('',403,'Forbidden',{},None)):
            with self.assertRaisesRegex(Blocked,'HTTP 403'):evidence.metrics(c,RELEASE)

    def test_vm_memory_writer_runs_even_when_reconcile_bundle_unchanged(self):
        with patch('vm_agent.Path.read_text',return_value='MemTotal: 1000 kB\nMemAvailable: 700 kB\n'), patch('vm_agent.fetch') as fetch:
            vm_agent.measurements('mindaam')
        series=fetch.call_args.args[1]['timeSeries'][0]
        self.assertEqual(series['metric']['type'],'custom.googleapis.com/mindaam/host_memory_utilization')
        self.assertAlmostEqual(series['points'][0]['value']['doubleValue'],.3)
        source=(HERE/'vm_agent.py').read_text()
        self.assertLess(source.index('measurements(project)',source.index('def main')),source.index('if marker.exists()'))

    def test_apex_routing_preserves_media_turn_and_websocket_proxy(self):
        config=caddy_config('https://mindaam-production-123.run.app');apps=config['apps']
        self.assertEqual(apps['tls']['certificates']['automate'],['media.mindaam.com','turn.mindaam.com','mindaam.com'])
        self.assertEqual(len(apps['layer4']['servers']['main']['routes']),3)
        proxy=apps['http']['servers']['app']['routes'][0]['handle'][0]
        self.assertEqual(proxy['handler'],'reverse_proxy')
        self.assertEqual(proxy['headers']['request']['set']['X-Forwarded-Proto'],['https'])
        self.assertEqual(proxy['transport']['tls']['server_name'],'mindaam-production-123.run.app')

    def test_verify_review_production_then_dns_finalize(self):
        c=Cloud('mindaam');objects={'foundation.json':{'project':'mindaam','media_ip':'34.13.51.100'},f'releases/{SHA}/staging.json':copy.deepcopy(RELEASE)}
        services={'staging':ready(c,'staging',RELEASE['revision'])};calls=[];backups=[];vm_bundles=[]
        def gc(*args,**kwargs):
            calls.append(args)
            if args[:3]==('run','services','describe'): return services.get(args[3].removeprefix('mindaam-'))
            if args[:3]==('run','services','replace'):
                manifest=json.loads(Path(args[3]).read_text());self.assertEqual(manifest['metadata']['name'],'mindaam-production')
                self.assertEqual(manifest['metadata']['annotations']['run.googleapis.com/maxScale'],'2')
                services['production']=ready(c,'production','production-00001');return {}
            if args[:3]==('run','services','add-iam-policy-binding'):return {}
            if args[:3]==('run','jobs','describe'):return None
            if args[:3] in [('run','jobs','deploy'),('run','jobs','execute')]:return {}
            if args[:3]==('sql','backups','create'):backups.append(args);return {}
            if args[:3]==('sql','databases','list'):return [{'name':'mindaam_staging'},{'name':'mindaam_production'}]
            if args[:3]==('sql','backups','list'):return [{'id':'test-backup','status':'SUCCESSFUL'}]
            if args[:3]==('sql','instances','describe'):return {'name':'mindaam-postgres','labels':{'application':'mindaam'},'settings':{'tier':'db-f1-micro'}}
            if args[:3]==('compute','instances','describe'):return {'name':'mindaam-media','labels':{'application':'mindaam'},'machineType':'e2-small','id':'123'}
            if args[:3]==('secrets','versions','list'):return []
            self.fail('Unexpected provider action '+repr(args))
        def put(key,value):objects[key]=copy.deepcopy(value)
        measured={'series':{'custom.googleapis.com/mindaam/host_memory_utilization':{'timeSeries':[{'points':[{'value':{'doubleValue':.3}}]}]}}}
        measured['series']['cloudsql.googleapis.com/database/memory/components']={'timeSeries':[
            {'metric':{'labels':{'component':k}},'points':[{'interval':{'endTime':f'2026-10-29T00:0{i}:00Z'},'value':{'doubleValue':v}} for i in range(3)]}
            for k,v in [('Usage',30),('Cache',20),('Free',50)]]}
        with tempfile.TemporaryDirectory() as directory:
            old=os.getcwd();os.chdir(directory)
            try:
                Path('gcp-evidence').mkdir()
                for name,forced in [('direct',False),('relay',True),('browser',True)]:
                    Path(f'gcp-evidence/{name}.json').write_text(json.dumps({'sha':SHA,'origin':ORIGIN,'forced_turn':forced,'checks':dict.fromkeys(evidence.REQUIRED_CHECKS,True)}))
                with patch.object(c,'require_project'), patch.object(c,'gc',side_effect=gc), \
                     patch.object(c,'get_json',side_effect=lambda k:copy.deepcopy(objects.get(k))), patch.object(c,'put_json',side_effect=put), \
                     patch('evidence.check',return_value={'mock':True}), patch('evidence.bounded_http',return_value=[{'mock':True}]), patch('evidence.metrics',return_value=measured), \
                     patch('workflow.Cloud',return_value=c), patch('workflow.check',return_value={'mock':True}), \
                     patch('workflow.subprocess.run',return_value=subprocess.CompletedProcess([],0)), patch('workflow.summary'), patch('deploy.summary'), \
                     patch('deploy.vm_bundle',side_effect=lambda *a,**kw:vm_bundles.append(kw)), patch.dict(os.environ,{'OPERATION':'verify','MINDAAM_PROJECT_ID':'mindaam','RELEASE_SHA':SHA}):
                    workflow.main();self.assertFalse(any(a[:2]==('run','jobs') for a in calls))
                    relay_path=Path('gcp-evidence/relay.json'); valid_relay=relay_path.read_text()
                    invalid=json.loads(valid_relay);invalid['checks']['turn_tls']=False;relay_path.write_text(json.dumps(invalid))
                    with self.assertRaisesRegex(Blocked,'Direct/relay'):evidence.verify(c,SHA)
                    relay_path.write_text(valid_relay)
                    evidence.verify(c,SHA)
                    packet=review.packet(c,SHA);self.assertFalse(packet['owner_approved']);self.assertIsNone(packet['pricing_date'])
                    with self.assertRaises(Blocked):review.save(c,SHA,copy.deepcopy(packet))
                    packet['pricing_date']=datetime.date.today().isoformat();packet['owner_approved']=True
                    for model in packet['costs'].values():model.update(assumptions={'mock':'test only'},pricing_sources=['https://cloud.google.com/run/pricing'],usd=dict.fromkeys(model['usd'],1))
                    for field, bad in [('pricing_date','2000-01-01'),('owner_approved',False),('resource_metrics_evidence','gs://unrelated/metrics.json')]:
                        invalid=copy.deepcopy(packet);invalid[field]=bad
                        with self.assertRaises(Blocked):review.save(c,SHA,invalid)
                    invalid=copy.deepcopy(packet);invalid['costs']['light']['assumptions']={'hours':None}
                    with self.assertRaises(Blocked):review.save(c,SHA,invalid)
                    invalid=copy.deepcopy(packet);invalid['costs']['light']['usd']['network']=151
                    with self.assertRaises(Blocked):review.save(c,SHA,invalid)
                    review.save(c,SHA,packet)
                    os.environ['OPERATION']='production';os.environ['REVIEW_OBJECT']=f'releases/{SHA}/release-review.json'
                    workflow.main()
                    self.assertEqual(len(backups),1);self.assertEqual(len(vm_bundles),1)
                    self.assertIn(f'releases/{SHA}/production-provider-verified.json',objects)
                    self.assertNotIn(f'releases/{SHA}/production-verified.json',objects)
                    before=len(calls)
                    with patch('finalize.socket.getaddrinfo',return_value=[(None,None,None,None,('34.13.51.100',443))]), patch('finalize.check',return_value={'mock':True}):
                        finalize.finalize(c,SHA);finalize.finalize(c,SHA)
                    self.assertIn(f'releases/{SHA}/production-verified.json',objects)
                    self.assertTrue(all(a[:3]==('run','services','describe') for a in calls[before:]))
                    self.assertEqual(objects['foundation.json']['media_ip'],'34.13.51.100')
                    services['production']['status']['latestReadyRevisionName']='different'
                    services['production']['status']['latestCreatedRevisionName']='different'
                    with self.assertRaises(Blocked):finalize.finalize(c,SHA)
            finally:os.chdir(old)

    def test_browser_contract_node_checks(self):
        subprocess.run(['node',str(HERE/'tests'/'browser-contract.cjs')],check=True)
