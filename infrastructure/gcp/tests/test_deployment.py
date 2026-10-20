import copy
import json
import math
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Cloud, Blocked, SETTINGS, command
from deploy import ensure, release_gate, image_check, startup_script
from render import service, caddy_config, compose_config
from source_gate import application_path


class FakeCloud(Cloud):
    def __init__(self):
        super().__init__('mindaam-production'); self.calls = []; self.objects = {}
    def gc(self, *args, **kwargs):
        self.calls.append((args, kwargs)); return self.objects.get(args)
    def get_json(self, key):
        return self.objects.get(key)


class DeploymentSafety(unittest.TestCase):
    def test_missing_never_hides_permission_errors(self):
        for error in ['PERMISSION_DENIED: object does not exist', '403 NOT_FOUND', 'permission denied; was not found', 'UNAUTHENTICATED', 'connection timed out']:
            with self.subTest(error=error), patch('common.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', error)):
                with self.assertRaises(Blocked): command(['unused'], allow_missing=True)
        with patch('common.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'NOT_FOUND')):
            self.assertIsNone(command(['unused'], allow_missing=True))

    def test_sensitive_errors_are_redacted(self):
        with patch('common.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'password=DO-NOT-PRINT')):
            with self.assertRaises(Blocked) as error: command(['unused'], sensitive=True)
            self.assertNotIn('DO-NOT-PRINT', str(error.exception))

    def test_unrelated_project_and_resources_rejected(self):
        for project in ['railway', 'other-production', 'mindaam-a;rm', 'mindaam-'+'x'*30]:
            with self.assertRaises(Blocked): Cloud(project)
        c=FakeCloud(); c.objects[('describe',)]={'labels':{'application':'other'}}
        with self.assertRaises(Blocked): ensure(c,['describe'],['create'],name='test')
        self.assertEqual(len(c.calls),1)

    def test_resume_keeps_existing_owned_resources(self):
        c=FakeCloud(); c.objects[('describe',)]={'labels':{'application':'mindaam'},'id':'same'}
        self.assertEqual(ensure(c,['describe'],['create'],name='test')['id'],'same')
        self.assertEqual([call[0] for call in c.calls],[('describe',)])

    def test_cloud_run_caps_origins_and_runtime_identity(self):
        c=FakeCloud()
        for env, maximum in [('staging','1'),('production','2')]:
            manifest=service(c,env,'example@sha256:'+'1'*64,'https://exact.run.app')
            self.assertEqual(manifest['metadata']['annotations']['run.googleapis.com/maxScale'],maximum)
            annotations=manifest['spec']['template']['metadata']['annotations']
            self.assertEqual(annotations['autoscaling.knative.dev/minScale'],'0')
            self.assertEqual(annotations['autoscaling.knative.dev/maxScale'],maximum)
            spec=manifest['spec']['template']['spec']; self.assertEqual(spec['serviceAccountName'],c.sa(env))
            values={v['name']:v for v in spec['containers'][0]['env']}
            self.assertEqual(values['PUBLIC_ORIGIN']['value'],'https://exact.run.app')
            self.assertEqual(values['RUN_MIGRATIONS_ON_START']['value'],'false')
            self.assertNotIn('value',values['DATABASE_URL'])
            self.assertEqual(values['LIVEKIT_URL']['value'],'wss://media.mindaam.com')
            self.assertEqual(values['DB_POOL_SIZE']['value'],'3')

    def test_image_cannot_come_from_other_project_or_mutable_tag(self):
        c=FakeCloud(); image_check(c,'europe-west2-docker.pkg.dev/mindaam-production/mindaam/app@sha256:'+'a'*64)
        for image in ['europe-west2-docker.pkg.dev/other/mindaam/app@sha256:'+'a'*64,'mindaam:latest']:
            with self.assertRaises(Blocked): image_check(c,image)

    def test_apex_proxy_cannot_target_an_arbitrary_service(self):
        for origin in ['http://app.run.app','https://evil.example','https://app.run.app/path']:
            with self.assertRaises(ValueError): caddy_config(origin)
        config=caddy_config('https://mindaam-production-123.europe-west2.run.app')
        self.assertEqual(len(config['apps']['layer4']['servers']['main']['routes']),3)
        self.assertIn('turn.mindaam.com',config['apps']['tls']['certificates']['automate'])

    def test_redis_entrypoint_does_not_need_disallowed_chown_capability(self):
        config=compose_config()['services']
        self.assertEqual(config['redis']['entrypoint'],['redis-server'])
        for service_ in config.values():
            self.assertRegex(service_['image'],r'@sha256:[a-f0-9]{64}$')
            self.assertEqual(service_['cap_drop'],['ALL'])
            self.assertTrue(service_['read_only'])
        self.assertNotIn('6379',json.dumps(config.get('ports',{})))

    def test_preserved_application_policy(self):
        root=Path(__file__).resolve().parents[3]
        policy=json.loads((root/'shared/media-policy.json').read_text())
        self.assertFalse(policy['auto_subscribe']); self.assertTrue(policy['dynacast']); self.assertTrue(policy['adaptive_stream'])
        self.assertFalse(policy['default_video']); self.assertFalse(policy['allow_1080p'])
        self.assertEqual(policy['avatar_video_max'],360); self.assertEqual(policy['fullscreen_video_max'],720)
        self.assertEqual(policy['auditorium_max_stage_video'],4); self.assertEqual(policy['auditorium_max_screen_share'],1)
        self.assertTrue(application_path('backend/api/snapshot.py')); self.assertTrue(application_path('shared/media-policy.json'))
        self.assertTrue(application_path('scripts/tests/multiplayer-browser.cjs')); self.assertFalse(application_path('infrastructure/gcp/deploy.py'))

    def test_production_rejects_absent_stale_wrong_or_failed_evidence(self):
        c,sha,image=self.review()
        release_gate(c,image,sha)
        evidence=c.objects[f'releases/{sha}/staging-verified.json']
        for key,value in [('verified_at',0),('sha','b'*40),('image','wrong')]:
            original=evidence[key]; evidence[key]=value
            with self.assertRaises(Blocked): release_gate(c,image,sha)
            evidence[key]=original
        evidence['checks']['turn_tls']=False
        with self.assertRaises(Blocked): release_gate(c,image,sha)

    def test_costs_fail_closed_not_nan_bool_or_unapproved_overspend(self):
        for value in [float('nan'),float('inf'),True,-1,151]:
            c,sha,image=self.review(); review=c.objects[f'releases/{sha}/release-review.json']
            review['costs']['light']['usd']['network']=value
            with self.assertRaises(Blocked): release_gate(c,image,sha)
        c,sha,image=self.review(); c.objects[f'releases/{sha}/release-review.json']['owner_approved']='true'
        with self.assertRaises(Blocked): release_gate(c,image,sha)

    def review(self):
        c=FakeCloud(); sha='a'*40; image='image-digest'
        c.objects[f'releases/{sha}/staging-verified.json']={'sha':sha,'image':image,'verified_at':int(time.time()),'checks':{k:True for k in ['browser','multiplayer','voice','video','screen_share','event_media','turn_tls','startup_policy','performance']}}
        components=['cloud_run','compute_livekit','postgresql','redis','storage','network','logging','other']
        c.objects[f'releases/{sha}/release-review.json']={'sha':sha,'image':image,'reviewed_at':int(time.time()),'owner_approved':True,'resource_metrics_evidence':f'gs://{c.bucket}/releases/{sha}/metrics.json','costs':{scenario:{'assumptions':'test only','pricing_sources':['test only'],'usd':dict.fromkeys(components,1)} for scenario in ['idle','light']}}
        return c,sha,image


if __name__=='__main__': unittest.main()
