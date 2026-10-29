"""Cloud Run first deployment and resume; no cloud or Docker operations."""
import copy
import io
import tarfile
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Blocked, Cloud, command
import workflow
from deploy import deploy, migrate

SHA = 'f53898771471b96debf3a91b65fa0de015152982'
HEAD = 'b' * 40
DIGEST = 'sha256:435acb7cebf9dabf7dc5d24e14f72f6d7de91c9ec3d79979baf69ccfcb1d6d2e'
IMAGE = 'europe-west2-docker.pkg.dev/mindaam/mindaam/app@' + DIGEST


def absent(kind, name):
    noun = 'service' if kind == 'services' else 'job'
    return f'ERROR: (gcloud.run.{kind}.describe) Cannot find {noun} [{name}]'


class StagingResume(unittest.TestCase):
    def test_exact_artifact_image_absence_is_command_scoped_and_opt_in(self):
        args = ['gcloud', 'artifacts', 'docker', 'images', 'describe',
                'europe-west2-docker.pkg.dev/mindaam/mindaam/app:' + SHA]
        message = 'ERROR: (gcloud.artifacts.docker.images.describe) Image not found.'
        with patch('common.subprocess.run', return_value=subprocess.CompletedProcess(args, 1, '', message)):
            self.assertIsNone(command(args, allow_missing=True))
            self.assertIsNone(Cloud('mindaam').gc(*args[1:], missing=True))
            with self.assertRaises(Blocked): command(args)
            for wrong in [['gcloud','artifacts','repositories','describe','mindaam'],
                          args[:4]+['delete',args[5]], ['other',*args[1:]], args[:5]]:
                with self.subTest(wrong=wrong), self.assertRaises(Blocked):command(wrong, allow_missing=True)
        failures = ['PERMISSION_DENIED','UNAUTHENTICATED','401','403','invalid credentials',
                    'quota exceeded','network unreachable','DNS lookup failed','TLS handshake failed',
                    'connection timed out','INVALID_ARGUMENT','Invalid project','Invalid repository',
                    'Wrong project','Repository unavailable','Unexpected error',
                    'NOT_FOUND: Repository wrong-repo was not found',
                    'Repository wrong-repo does not exist', 'NOT_FOUND: Invalid repository']
        for failure in failures:
            for payload in [failure, message+'\n'+failure, failure+'\n'+message]:
                with self.subTest(payload=payload), patch('common.subprocess.run', return_value=
                        subprocess.CompletedProcess(args,1,'',payload)), self.assertRaises(Blocked):
                    command(args, allow_missing=True)
        for payload in ['Image not found.', message+' extra text', 'ERROR: (other) Image not found.']:
            with patch('common.subprocess.run', return_value=subprocess.CompletedProcess(args,1,'',payload)), self.assertRaises(Blocked):
                command(args, allow_missing=True)

    def test_missing_feature_image_builds_exact_ancestor_then_deploys_and_resumes(self):
        self.scenario(job_exists=True, missing_image=True, service_exists=True)

    def test_exact_run_missing_requires_matching_command_and_opt_in(self):
        for kind, name in [('services', 'mindaam-staging'), ('services', 'mindaam-production'),
                           ('jobs', 'mindaam-migrate-staging'), ('jobs', 'mindaam-migrate-production')]:
            args = ['gcloud', 'run', kind, 'describe', name, '--region=europe-west2']
            with self.subTest(name=name), patch('common.subprocess.run', return_value=
                    subprocess.CompletedProcess(args, 1, '', absent(kind, name))):
                self.assertIsNone(command(args, allow_missing=True))
                self.assertIsNone(Cloud('mindaam').gc(*args[1:], missing=True))
                with self.assertRaises(Blocked):
                    command(args)
                with self.assertRaises(Blocked):
                    command(['gcloud', 'run', kind, 'describe', 'unrelated'], allow_missing=True)

    def test_punctuated_provider_absence_remains_scoped_and_fail_closed(self):
        for kind, name in [('services', 'mindaam-production'), ('jobs', 'mindaam-migrate-production')]:
            args = ['gcloud', 'run', kind, 'describe', name]
            message = absent(kind, name) + '.'
            with patch('common.subprocess.run', return_value=subprocess.CompletedProcess(args, 1, '', message)):
                self.assertIsNone(command(args, allow_missing=True))
                with self.assertRaises(Blocked): command(args)
                with self.assertRaises(Blocked): command(args[:4] + ['unrelated'], allow_missing=True)
            for suffix in [' extra text', '\nPERMISSION_DENIED', '\nTLS handshake failed']:
                with patch('common.subprocess.run', return_value=subprocess.CompletedProcess(args, 1, '', message + suffix)):
                    with self.assertRaises(Blocked): command(args, allow_missing=True)

    def test_run_errors_are_fatal(self):
        args = ['gcloud', 'run', 'services', 'describe', 'mindaam-staging']
        errors = ['PERMISSION_DENIED', 'UNAUTHENTICATED', '401', '403', 'invalid credentials',
                  'INVALID_ARGUMENT', 'quota exceeded', 'network unreachable', 'DNS lookup failed',
                  'TLS handshake failed', 'connection timed out', 'Wrong project', 'Wrong region',
                  'Invalid service name', 'Malformed resource name', 'Unknown region',
                  'Project wrong-project does not exist', 'Region invalid-region was not found']
        for error in errors:
            for message in [error, absent('services', 'mindaam-staging') + '\n' + error]:
                with self.subTest(message=message), patch('common.subprocess.run', return_value=
                        subprocess.CompletedProcess(args, 1, '', message)):
                    with self.assertRaises(Blocked):
                        command(args, allow_missing=True)
        for name in ['mindaam_staging', '../mindaam-staging', 'mindaam-staging/other', 'unrelated']:
            with self.subTest(name=name), patch('common.subprocess.run', return_value=
                    subprocess.CompletedProcess([], 1, '', absent('services', name))):
                with self.assertRaises(Blocked):
                    command(args[:4] + [name], allow_missing=True)

    def test_first_staging_and_resume_reuse_available_image(self):
        self.scenario(job_exists=False)

    def test_current_resume_keeps_existing_migration_job(self):
        self.scenario(job_exists=True)

    def scenario(self, job_exists, missing_image=False, service_exists=False):
        cloud = Cloud('mindaam')
        objects = {'foundation.json': {'project': 'mindaam', 'media_ip': '34.13.51.100'}}
        original_foundation = copy.deepcopy(objects['foundation.json'])
        current = None
        if service_exists:
            from render import service
            current = service(cloud, 'staging', IMAGE, 'https://mindaam-staging-123.europe-west2.run.app')
            current['status'] = {'url':'https://mindaam-staging-123.europe-west2.run.app',
                'latestReadyRevisionName':'old-revision','latestCreatedRevisionName':'old-revision',
                'conditions':[{'type':'Ready','status':'True'}]}
        actions = []
        job = {'metadata': {'labels': {'application': 'mindaam'}}} if job_exists else None
        counts = {'service_creates': 0, 'job_creates': 0, 'executions': 0, 'image_lookups': 0}
        manifests = []

        def run(args, **kwargs):
            nonlocal current, job
            data = {}
            if args[:3] == ['git', 'merge-base', '--is-ancestor']:
                return subprocess.CompletedProcess(args, 0, '', '')
            if args == ['git', 'rev-parse', 'HEAD']:
                return subprocess.CompletedProcess(args, 0, HEAD, '')
            if args[:3] == ['git', 'diff', '--name-only']:
                return subprocess.CompletedProcess(args, 0, 'infrastructure/gcp/common.py\ninfrastructure/gcp/workflow.py', '')
            if args[:2] == ['git', 'archive']:
                self.assertTrue(missing_image);self.assertEqual(args[-1], SHA)
                target=next(a.split('=',1)[1] for a in args if a.startswith('--output='))
                with tarfile.open(target,'w') as archive:
                    data=b'FROM exact-requested-release';entry=tarfile.TarInfo('infrastructure/gcp/Dockerfile');entry.size=len(data)
                    archive.addfile(entry,io.BytesIO(data))
                actions.append('archive');return subprocess.CompletedProcess(args,0,'','')
            if args[:2] == ['docker', 'build']:
                self.assertTrue(missing_image)
                self.assertEqual(Path(args[args.index('-f')+1]).read_bytes(),b'FROM exact-requested-release')
                self.assertNotEqual(args[-1],'.');self.assertTrue(args[args.index('-t')+1].endswith(':'+SHA))
                actions.append('build');return subprocess.CompletedProcess(args,0,'','')
            if args[:2] == ['docker', 'push']:
                self.assertEqual(actions[-1],'build');actions.append('push')
                return subprocess.CompletedProcess(args,0,'','')
            self.assertEqual(args[0], 'gcloud')
            self.assertIn('--project=mindaam', args)
            a = args[1:]
            if a[:4] == ['artifacts', 'docker', 'images', 'describe']:
                self.assertEqual(a[4], 'europe-west2-docker.pkg.dev/mindaam/mindaam/app:' + SHA)
                counts['image_lookups'] += 1
                if missing_image and counts['image_lookups'] == 1:
                    return subprocess.CompletedProcess(args,1,'','ERROR: (gcloud.artifacts.docker.images.describe) Image not found.')
                data = {'image_summary': {'digest': DIGEST}}
            elif a[:2] == ['auth','configure-docker']:
                self.assertTrue(missing_image)
            elif a[:3] == ['run', 'services', 'describe']:
                self.assertEqual(a[3], 'mindaam-staging')
                self.assertIn('--region=europe-west2', a)
                if current is None:
                    return subprocess.CompletedProcess(args, 1, '', absent('services', a[3]))
                data = current
            elif a[:3] == ['run', 'jobs', 'describe']:
                if job is None:
                    return subprocess.CompletedProcess(args, 1, '', absent('jobs', a[3]))
                data = job
            elif a[:3] == ['run', 'jobs', 'deploy']:
                self.assertIn('--image=' + IMAGE, a)
                self.assertIn('--service-account=' + cloud.sa('migrate'), a)
                self.assertIn('--max-retries=0', a)
                self.assertIn('--set-env-vars=APP_ENV=staging', a)
                counts['job_creates'] += int(job is None)
                job = {'metadata': {'labels': {'application': 'mindaam'}}}
            elif a[:3] == ['run', 'jobs', 'execute']:
                self.assertIsNotNone(job)
                self.assertIn('--wait', a)
                counts['executions'] += 1
                actions.append('migration')
            elif a[:3] == ['run', 'services', 'replace']:
                manifest = json.loads(Path(a[3]).read_text())
                self.assertEqual(manifest['metadata']['name'], 'mindaam-staging')
                self.assertEqual(manifest['metadata']['annotations']['run.googleapis.com/maxScale'], '1')
                template = manifest['spec']['template']
                self.assertEqual(template['spec']['containers'][0]['image'], IMAGE)
                self.assertEqual(template['metadata']['annotations']['autoscaling.knative.dev/minScale'], '0')
                counts['service_creates'] += int(current is None)
                manifests.append(manifest)
                actions.append('deploy')
                current = {**manifest, 'status': {'url': 'https://mindaam-staging-123.europe-west2.run.app',
                    'latestReadyRevisionName': 'mindaam-staging-00001', 'latestCreatedRevisionName': 'mindaam-staging-00001',
                    'conditions': [{'type': 'Ready', 'status': 'True'}]}}
            elif a[:3] == ['run', 'services', 'add-iam-policy-binding']:
                self.assertIsNotNone(current)
                values = {e['name']: e.get('value') for e in current['spec']['template']['spec']['containers'][0]['env']}
                self.assertEqual(values['PUBLIC_ORIGIN'], current['status']['url'])
            elif a[:3] == ['secrets', 'versions', 'list']:
                data = []  # Reads only; any secret mutation falls through and fails.
            else:
                self.fail('Unexpected mutation or command: ' + repr(a))
            return subprocess.CompletedProcess(args, 0, json.dumps(data), '')

        def put(key, value):
            self.assertTrue(key.startswith(f'releases/{SHA}/'))
            objects[key] = copy.deepcopy(value)

        with tempfile.TemporaryDirectory() as directory:
            cwd = os.getcwd()
            try:
                os.chdir(directory)
                with patch('common.subprocess.run', side_effect=run), \
                     patch('workflow.Cloud', return_value=cloud), patch.object(cloud, 'require_project'), \
                     patch.object(cloud, 'get_json', side_effect=lambda key: copy.deepcopy(objects.get(key))), \
                     patch.object(cloud, 'put_json', side_effect=put), patch('deploy.summary'), \
                     patch('workflow.check', return_value={'ok': True}), \
                     patch.dict(os.environ, {'OPERATION': 'staging', 'MINDAAM_PROJECT_ID': 'mindaam', 'RELEASE_SHA': SHA}):
                    workflow.main()
                    workflow.main()
                self.assertEqual(json.loads(Path('deployment-result.json').read_text())['image'], IMAGE)
            finally:
                os.chdir(cwd)
        self.assertEqual(counts, {'service_creates': 0 if service_exists else 1, 'job_creates': 0 if job_exists else 1,
                                 'executions': 2, 'image_lookups': 2 if missing_image else 1})
        self.assertEqual(objects['foundation.json'], original_foundation)
        self.assertEqual(objects[f'releases/{SHA}/staging.json']['image'], IMAGE)
        self.assertEqual(len(manifests), 2 if service_exists else 3)  # Initial create + origin fix, then owned service update.

        if missing_image:
            self.assertEqual(actions, ['archive','build','push','migration','deploy','migration','deploy'])

    def test_unowned_service_blocks_before_migration(self):
        cloud = Cloud('mindaam')
        with patch.object(cloud, 'require_project'), patch.object(cloud, 'get_json', return_value={'project': 'mindaam'}), \
             patch.object(cloud, 'gc', return_value={'metadata': {'labels': {'application': 'other'}}}) as gc:
            with self.assertRaises(Blocked):
                deploy(cloud, 'staging', IMAGE, SHA)
        gc.assert_called_once_with('run', 'services', 'describe', 'mindaam-staging', '--region=europe-west2', missing=True)

    def test_unowned_migration_job_is_never_deployed_or_executed(self):
        cloud = Cloud('mindaam')
        with patch.object(cloud, 'gc', return_value={'metadata': {'labels': {}}}) as gc:
            with self.assertRaises(Blocked):
                migrate(cloud, 'staging', IMAGE)
        gc.assert_called_once()

    def test_image_reuse_failures_do_not_build(self):
        cloud = Cloud('mindaam')
        for info in [None, {}, {'image_summary': {'digest': 'latest'}}]:
            with self.subTest(info=info), patch.object(cloud, 'get_json', return_value=None), \
                 patch.object(cloud, 'gc', return_value=info), patch('workflow.subprocess.run') as run:
                with self.assertRaises(Blocked):
                    workflow.staging_image(cloud, SHA, build_allowed=False)
                run.assert_not_called()
        with patch.object(cloud, 'get_json', return_value=None), \
             patch.object(cloud, 'gc', side_effect=Blocked('PERMISSION_DENIED')), patch('workflow.subprocess.run') as run:
            with self.assertRaises(Blocked):
                workflow.staging_image(cloud, SHA, build_allowed=True)
            run.assert_not_called()

    def test_old_release_with_changed_build_inputs_is_rejected(self):
        cloud = Cloud('mindaam')
        for path in ['backend/app.py', 'infrastructure/gcp/migrate.py', 'infrastructure/gcp/Dockerfile', '.dockerignore']:
            with self.subTest(path=path), patch('workflow.Cloud', return_value=cloud), \
                 patch.object(cloud, 'require_project'), patch('workflow.subprocess.run', return_value=subprocess.CompletedProcess([], 0)), \
                 patch('workflow.command', side_effect=[HEAD, path]), patch.object(cloud, 'gc') as gc, \
                 patch.dict(os.environ, {'OPERATION': 'staging', 'MINDAAM_PROJECT_ID': 'mindaam', 'RELEASE_SHA': SHA}):
                with self.assertRaises(Blocked):
                    workflow.main()
                gc.assert_not_called()

    def test_missing_current_image_builds_once_then_pins_digest(self):
        cloud = Cloud('mindaam')
        with patch.object(cloud, 'get_json', return_value=None), \
             patch.object(cloud, 'gc', side_effect=[None, None, {'image_summary': {'digest': DIGEST}}]) as gc, \
             patch('workflow.subprocess.run') as run:
            self.assertEqual(workflow.staging_image(cloud, SHA, build_allowed=True), IMAGE)
        self.assertEqual([call.args[0][:2] for call in run.call_args_list],
                         [['docker', 'build'], ['docker', 'push']])
        self.assertEqual(gc.call_args_list[0].kwargs, {'missing': True})
        self.assertNotIn('missing', gc.call_args_list[-1].kwargs)

    def test_recorded_image_must_belong_to_exact_release_and_repository(self):
        cloud = Cloud('mindaam')
        for state in [{'sha': HEAD, 'environment': 'staging', 'image': IMAGE},
                      {'sha': SHA, 'environment': 'production', 'image': IMAGE},
                      {'sha': SHA, 'environment': 'staging', 'image': IMAGE.replace('/mindaam/', '/other/', 1)}]:
            with self.subTest(state=state), patch.object(cloud, 'get_json', return_value=state), \
                 patch.object(cloud, 'gc') as gc:
                with self.assertRaises(Blocked):
                    workflow.staging_image(cloud, SHA, build_allowed=False)
                gc.assert_not_called()
