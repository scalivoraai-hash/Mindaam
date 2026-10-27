"""First-deployment discovery regressions; never contact Google Cloud."""
import subprocess
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Blocked, Cloud, command
from deploy import bucket, ensure, foundation, ensure_postgres, DESCRIPTION, OPTIONAL
from common import SETTINGS

STORAGE_MISSING = 'ERROR: (gcloud.storage.buckets.describe) gs://mindaam-releases not found: 404.'
IDENTITY = (' This command is authenticated as mindaam-deploy@mindaam.iam.gserviceaccount.com'
            ' using the credentials ...')
SQL_MISSING = ('ERROR: (gcloud.sql.databases.describe) HTTPError 404: Not Found.' +
               IDENTITY.replace('credentials ...', 'credentials in '
                   '/home/runner/work/Mindaam/Mindaam/gha-creds-cb272febf1799868.json, '
                   'specified by the [auth/credential_file_override] property'))
STORAGE_CAT_HEADER = ('ERROR: (gcloud.storage.cat) '
                      'The following URLs matched no objects or files:')
STORAGE_CAT_MISSING = STORAGE_CAT_HEADER + '\n' + 'gs://mindaam-releases/vm/current.json'
# Include SQL databases and VM bundle metadata as well as the requested resources.
DISCOVERY = [
    ('artifacts.repositories.describe', 'mindaam'),
    ('compute.networks.describe', 'projects/mindaam/global/networks/mindaam'),
    ('compute.networks.subnets.describe', 'mindaam-run'),
    ('compute.firewall-rules.describe', 'mindaam-media-public'),
    ('compute.firewall-rules.describe', 'mindaam-redis-private'),
    ('compute.addresses.describe', 'mindaam-media'),
    ('secrets.describe', 'mindaam-postgres-password'),
    ('secrets.describe', 'mindaam-production-smtp-password'),
    ('sql.instances.describe', 'mindaam-postgres'),
    ('sql.databases.describe', 'mindaam_staging'),
    ('sql.databases.describe', 'mindaam_production'),
    ('compute.instances.describe', 'mindaam-media'),
    ('storage.buckets.describe', 'gs://mindaam-releases'),
    ('storage.buckets.describe', 'gs://mindaam-assets'),
    ('storage.cat', 'gs://mindaam-releases/vm/current.json'),
]


class MissingResources(unittest.TestCase):
    def result(self, error):
        return subprocess.CompletedProcess([], 1, '', error)

    def test_exact_storage_cat_missing_requires_explicit_opt_in(self):
        with patch('common.subprocess.run', return_value=self.result(STORAGE_CAT_MISSING)):
            self.assertIsNone(command(['gcloud', 'storage', 'cat',
                'gs://mindaam-releases/vm/current.json'], allow_missing=True))
            with self.assertRaises(Blocked):
                command(['gcloud', 'storage', 'cat', 'gs://mindaam-releases/vm/current.json'])

    def test_all_optional_state_reads_share_missing_handling(self):
        keys = ['foundation.json', 'vm/current.json'] + [
            'releases/' + 'a' * 40 + '/' + name + '.json' for name in
            ['staging', 'production', 'staging-previous', 'production-previous',
             'staging-verified', 'production-verified', 'release-review', 'metrics']]
        for key in keys:
            url = 'gs://mindaam-releases/' + key
            with self.subTest(key=key), patch('common.subprocess.run',
                    return_value=self.result(STORAGE_CAT_HEADER + '\n' + url)) as run:
                self.assertIsNone(Cloud('mindaam').get_json(key))
                self.assertEqual(run.call_args.args[0],
                    ['gcloud', 'storage', 'cat', url, '--project=mindaam'])
                run.assert_called_once()
        with patch('common.subprocess.run', return_value=subprocess.CompletedProcess(
                [], 0, '{"production_origin":"https://existing.run.app"}', '')):
            self.assertEqual(Cloud('mindaam').get_json('vm/current.json'),
                             {'production_origin': 'https://existing.run.app'})
        with patch('common.subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'bad json', '')):
            with self.assertRaises(json.JSONDecodeError):
                Cloud('mindaam').get_json('vm/current.json')

    def test_storage_cat_real_failures_remain_fatal(self):
        for error in ['PERMISSION_DENIED', 'UNAUTHENTICATED', '401', '403',
                      'invalid credentials', 'quota exceeded', 'network unreachable',
                      'DNS lookup failed', 'TLS handshake failed', 'connection timed out',
                      'INVALID_ARGUMENT', 'invalid request', 'malformed request',
                      'Invalid URL', 'Malformed path', 'HTTPError 500: Internal Server Error']:
            for message in [error, error + '\n' + STORAGE_CAT_MISSING,
                            STORAGE_CAT_MISSING + '\n' + error]:
                with self.subTest(message=message), patch('common.subprocess.run',
                        return_value=self.result(message)):
                    with self.assertRaises(Blocked):
                        Cloud('mindaam').get_json('vm/current.json')
        for error in ['Storage access failed', 'Unexpected storage error',
                      'ERROR: gs://bucket/The following URLs matched no objects or files:']:
            with self.subTest(error=error), patch('common.subprocess.run', return_value=self.result(error)):
                with self.assertRaises(Blocked):
                    Cloud('mindaam').get_json('vm/current.json')

    def test_exact_cloud_sql_error_requires_explicit_missing(self):
        with patch('common.subprocess.run', return_value=self.result(SQL_MISSING)):
            self.assertIsNone(Cloud('mindaam').gc('sql', 'databases', 'describe',
                'mindaam_staging', '--instance=mindaam-postgres', missing=True))
            self.assertIsNone(command(['unused'], allow_missing=True))
            with self.assertRaises(Blocked):
                command(['unused'])

    def test_exact_artifact_registry_error_with_identity_context(self):
        error = ('ERROR: (gcloud.artifacts.repositories.describe) NOT_FOUND: '
                 'Requested entity was not found.' + IDENTITY)
        with patch('common.subprocess.run', return_value=self.result(error)):
            self.assertIsNone(command(['unused'], allow_missing=True))
            with self.assertRaises(Blocked):
                command(['unused'])

    def test_all_foundation_discovery_errors_with_identity_context(self):
        for cli, resource in DISCOVERY:
            for detail in [f'NOT_FOUND: Requested entity {resource} was not found.',
                           f"The resource '{resource}' was not found",
                           'HTTPError 404: Not Found.', 'HTTP 404: Not Found',
                           f'{resource} not found: 404.', 'No URLs matched: ' + resource,
                           f'{resource} does not exist']:
                with self.subTest(cli=cli, detail=detail), patch(
                    'common.subprocess.run', return_value=self.result(
                        f'ERROR: (gcloud.{cli}) {detail}' + IDENTITY)):
                    self.assertIsNone(Cloud('mindaam').gc(*cli.split('.'), resource, missing=True))
                    with self.assertRaises(Blocked):
                        Cloud('mindaam').gc(*cli.split('.'), resource)
        with patch('common.subprocess.run', return_value=self.result(STORAGE_MISSING + IDENTITY)):
            self.assertIsNone(command(['unused'], allow_missing=True))

    def test_real_failures_survive_identity_context_in_every_resource(self):
        errors = ['PERMISSION_DENIED', 'HTTP 403', 'UNAUTHENTICATED', 'HTTP 401',
                  'UNAUTHORIZED', 'FORBIDDEN', 'invalid credentials', 'credentials expired',
                  'authentication failed', 'Failed to obtain credentials',
                  'There was a problem refreshing your current auth tokens: invalid_grant',
                  'network unreachable', 'connection reset', 'DNS lookup failed',
                  'TLS handshake failed', 'SSL certificate error', 'connection timed out',
                  'name resolution failed', 'proxy error', 'transport error',
                  'RESOURCE_EXHAUSTED', 'quota exceeded', 'HTTPError 429: Too Many Requests',
                  'HTTPError 500: Internal Server Error', 'HTTPError 504: Gateway failure', 'INVALID_ARGUMENT',
                  'invalid argument', 'malformed request', 'HTTPError 400: Bad Request']
        for cli, resource in DISCOVERY:
            for error in errors:
                for message in [SQL_MISSING + '\n' + error, error + '\nNOT_FOUND' + IDENTITY,
                                'NOT_FOUND' + IDENTITY + '\n' + error,
                                'NOT_FOUND' + IDENTITY + ' ' + error]:
                    with self.subTest(cli=cli, error=error, message=message), patch(
                        'common.subprocess.run', return_value=self.result(
                            f'ERROR: (gcloud.{cli}) {resource}: {message}')):
                        with self.assertRaises(Blocked):
                            Cloud('mindaam').gc(*cli.split('.'), resource, missing=True)

    def test_first_foundation_creates_all_missing_resources(self):
        self.foundation_scenario()

    def test_partial_foundation_keeps_media_and_creates_private_redis(self):
        self.foundation_scenario(partial=True)

    def test_current_sql_partial_resume_reaches_completion(self):
        self.foundation_scenario(sql_partial=True)

    def test_current_gcs_partial_resume_reaches_completion(self):
        self.foundation_scenario(sql_partial=True, databases_exist=True)

    def test_database_discovery_failure_does_not_create(self):
        for error in ['HTTPError 403: Forbidden', 'HTTPError 401: Unauthorized',
                      'RESOURCE_EXHAUSTED: quota exceeded', 'INVALID_ARGUMENT',
                      'connection timed out', 'HTTPError 500: Internal Server Error']:
            with self.subTest(error=error):
                self.foundation_scenario(sql_partial=True, database_error=error)

    def foundation_scenario(self, partial=False, sql_partial=False, database_error=None, databases_exist=False):
        created, missing = set(), set()
        policies, versions = [], set()
        resuming = False
        initial = {('compute', 'firewall-rules', 'mindaam-media-public'),
                   ('secrets', 'mindaam-postgres-password')} if partial else set()
        if sql_partial:
            initial = {('storage', 'buckets', 'gs://mindaam-' + name)
                       for name in ('releases', 'assets')}
            initial.update({('artifacts', 'repositories', 'mindaam'),
                ('compute', 'networks', 'mindaam'),
                ('compute', 'networks', 'subnets', 'mindaam-run'),
                ('compute', 'firewall-rules', 'mindaam-media-public'),
                ('compute', 'firewall-rules', 'mindaam-redis-private'),
                ('compute', 'addresses', 'mindaam-media'),
                ('sql', 'instances', 'mindaam-postgres')})
            versions.update({'mindaam-postgres-password', 'mindaam-redis-password'})
            suffixes = ['database-password', 'database-url', 'migration-url', 'redis-url',
                        'livekit-key', 'livekit-secret', 'pulsepoint-secret',
                        'mail-encryption-key', 'owner-email', 'owner-username', 'owner-password']
            for env in ('staging', 'production'):
                versions.update(f'mindaam-{env}-{suffix}' for suffix in suffixes)
                initial.update(('secrets', f'mindaam-{env}-' + key.lower().replace('_', '-'))
                               for key in OPTIONAL)
            initial.update(('secrets', name) for name in versions)
        if databases_exist:
            initial.update({('sql', 'databases', 'mindaam_staging'),
                            ('sql', 'databases', 'mindaam_production')})
        initial_versions = set(versions)
        objects, user_updates, vm_creates = {}, [], []
        created.update(initial)
        if partial:
            versions.add('mindaam-postgres-password')
        resource = {
            'labels': {'application': 'mindaam'}, 'description': DESCRIPTION,
            'ipCidrRange': SETTINGS['subnet_cidr'], 'address': '192.0.2.1',
            'machineType': '/machineTypes/' + SETTINGS['vm_type'], 'state': 'RUNNABLE',
            'settings': {'tier': SETTINGS['sql_tier'], 'availabilityType': 'ZONAL',
                         'dataDiskSizeGb': '10', 'storageAutoResizeLimit': SETTINGS['sql_disk_limit_gb'],
                         'backupConfiguration': {'enabled': True}, 'ipConfiguration': {}},
        }

        def run(args, **kwargs):
            args = args[1:]
            if args[:2] == ['compute', 'firewall-rules']:
                self.assertIn(args[2], ['describe', 'create'], 'Never modify an existing firewall')
            data = {}
            if args[:2] == ['projects', 'describe']:
                data = {'lifecycleState': 'ACTIVE', 'projectNumber': '157480611225',
                        'labels': {'application': 'mindaam'}}
            elif args[:3] == ['billing', 'projects', 'describe']:
                data = {'billingEnabled': True}
            elif args[:2] == ['auth', 'print-access-token'] or args[:3] == ['secrets', 'versions', 'access']:
                return subprocess.CompletedProcess([], 0, 'test-only-value', '')
            elif args[:3] == ['artifacts', 'repositories', 'set-cleanup-policies']:
                policy = json.loads(Path(next(a.split('=', 1)[1] for a in args if a.startswith('--policy='))).read_text())
                self.assertEqual(policy, [
                    {'name': 'delete-untagged', 'action': {'type': 'Delete'},
                     'condition': {'tagState': 'untagged', 'olderThan': '604800s'}},
                    {'name': 'keep-recent', 'action': {'type': 'Keep'},
                     'mostRecentVersions': {'keepCount': 5}},
                ])
                self.assertIn('--no-dry-run', args)
                policies.append(policy)
            elif args[:3] == ['sql', 'users', 'set-password']:
                self.assertEqual(args[3:5], ['postgres', '--instance=mindaam-postgres'])
                payload = json.loads(Path(next(a.split('=', 1)[1] for a in args
                    if a.startswith('--flags-file='))).read_text())
                self.assertEqual(payload, {'--password': 'test-only-value'})
                user_updates.append(args[3])
            elif args[:2] == ['storage', 'cp']:
                if args[3].endswith('.json'):
                    objects[args[3]] = json.loads(Path(args[2]).read_text())
                else:
                    self.assertIn('/vm/bundles/', args[3])
                    self.assertTrue(Path(args[2]).read_bytes())
            elif args[:3] == ['secrets', 'versions', 'add']:
                self.assertFalse(sql_partial, 'All current-state secrets already have values')
                self.assertFalse(resuming, 'Resume must not regenerate existing secrets')
                self.assertNotIn(args[3], versions, 'Never regenerate an existing secret')
                versions.add(args[3])
            elif args[:3] == ['secrets', 'versions', 'list']:
                data = [{'state': 'ENABLED'}] if args[3] in versions else []
            elif args[:3] == ['storage', 'buckets', 'add-iam-policy-binding']:
                self.assertEqual(args[3], 'gs://mindaam-releases')
                self.assertIn('--member=serviceAccount:mindaam-media@mindaam.iam.gserviceaccount.com', args)
                self.assertIn('--role=roles/storage.objectViewer', args)
                self.assertIn("--condition=title=mindaam-vm-only,expression=resource.name.startsWith('projects/_/buckets/mindaam-releases/objects/vm/')", args)
                self.assertIn('--format=none', args)
            elif args[:2] == ['secrets', 'add-iam-policy-binding']:
                self.assertIn('--role=roles/secretmanager.secretAccessor', args)
                member = next(a for a in args if a.startswith('--member='))
                self.assertTrue(member.startswith('--member=serviceAccount:mindaam-'))
                self.assertTrue(member.endswith('@mindaam.iam.gserviceaccount.com'))
                self.assertIn('--format=none', args)
            elif 'create' in args:
                self.assertFalse(resuming, 'Resume must not recreate existing resources')
                i = args.index('create'); key = tuple(args[:i] + [args[i + 1]])
                self.assertNotIn(key, created, 'Never recreate an existing resource')
                if sql_partial:
                    self.assertIn(key, {('sql', 'databases', 'mindaam_staging'),
                        ('sql', 'databases', 'mindaam_production'),
                        ('compute', 'instances', 'mindaam-media')})
                if args[:2] == ['compute', 'instances']:
                    self.assertIn('--subnet=mindaam-run', args)
                    self.assertIn('--private-network-ip=' + SETTINGS['media_private_ip'], args)
                    self.assertIn('--address=192.0.2.1', args)
                    self.assertIn('--service-account=' + Cloud('mindaam').sa('media'), args)
                    script = Path(next(a.split('startup-script=', 1)[1] for a in args
                        if a.startswith('--metadata-from-file='))).read_text()
                    self.assertIn('set -euo pipefail', script)
                    self.assertIn('systemctl enable --now mindaam-reconcile.timer', script)
                    vm_creates.append(key)
                created.add(key)
            elif 'describe' in args:
                i = args.index('describe'); key = tuple(args[:i] + [args[i + 1]])
                if key not in created:
                    missing.add(key)
                    if args[:2] == ['sql', 'databases']:
                        return self.result(SQL_MISSING if database_error is None else database_error + IDENTITY)
                    return self.result(f'ERROR: (gcloud.{".".join(args[:i + 1])}) '
                                       f'NOT_FOUND: {key} was not found.' + IDENTITY)
                data = dict(resource)
                if args[:2] == ['compute', 'firewall-rules']:
                    private = key[-1] == 'mindaam-redis-private'
                    data.update(allowed=([{'IPProtocol': 'tcp', 'ports': ['6379']}] if private else
                        [{'IPProtocol': protocol, 'ports': [port]} for protocol, port in
                         [('tcp', '80'), ('tcp', '443'), ('tcp', '7881'), ('udp', '3478'), ('udp', '50000-50200')]]),
                        network='https://www.googleapis.com/compute/v1/projects/mindaam/global/networks/mindaam',
                        sourceRanges=[SETTINGS['subnet_cidr'] if private else '0.0.0.0/0'],
                        targetServiceAccounts=[Cloud('mindaam').sa('media')], direction='INGRESS')
            elif 'list' in args:
                data = []
            elif args[:2] == ['storage', 'cat']:
                if args[2] in objects:
                    return subprocess.CompletedProcess([], 0, json.dumps(objects[args[2]]), '')
                missing.add(('storage', 'cat', args[2]))
                return self.result(STORAGE_CAT_HEADER + '\n' + args[2])
            return subprocess.CompletedProcess([], 0, json.dumps(data), '')

        def sql_create(*args, **kwargs):
            self.assertFalse(sql_partial or resuming, 'Never recreate existing Cloud SQL')
            created.add(('sql', 'instances', 'mindaam-postgres'))
            return io.StringIO('{"name": "test-operation"}')

        with patch('common.subprocess.run', side_effect=run), \
             patch('deploy.urlopen', side_effect=sql_create), \
             patch.dict('os.environ', {'MINDAAM_BUDGET_CONFIRMED': 'true'}), \
             patch('deploy.summary'):
            if database_error is not None:
                with self.assertRaises(Blocked):
                    foundation(Cloud('mindaam'))
                self.assertEqual(created, initial)
                self.assertEqual(versions, initial_versions)
                self.assertFalse(objects)
                return
            foundation(Cloud('mindaam'))
            resuming = True
            foundation(Cloud('mindaam'))
        self.assertEqual(user_updates, ['postgres', 'postgres'])
        self.assertEqual(len(vm_creates), 1)
        self.assertIn('gs://mindaam-releases/vm/current.json', objects)
        inventory = objects['gs://mindaam-releases/foundation.json']
        self.assertEqual(inventory['project'], 'mindaam')
        self.assertEqual(inventory['media_ip'], '192.0.2.1')
        if sql_partial:
            self.assertEqual(versions, initial_versions)
        self.assertEqual(len(policies), 2)
        self.assertEqual(policies[0], policies[1])
        self.assertEqual(missing - {('storage', 'cat', 'gs://mindaam-releases/vm/current.json')}, created - initial)
        for cli, name in DISCOVERY:
            parts = cli.split('.')
            key = tuple(parts[:-1] + [name]) if parts[-1] == 'describe' else tuple(parts + [name])
            if cli == 'compute.networks.describe':
                key = ('compute', 'networks', 'mindaam')
            self.assertIn(key, missing | initial)

    def test_foundation_refuses_unowned_registry_before_policy_update(self):
        for labels in [{}, {'application': 'other'}]:
            cloud = Cloud('mindaam')
            with patch.object(cloud, 'require_project'), patch('deploy.bucket'), \
                 patch.dict('os.environ', {'MINDAAM_BUDGET_CONFIRMED': 'true'}), \
                 patch.object(cloud, 'gc', return_value={'labels': labels}) as gc:
                with self.assertRaises(Blocked):
                    foundation(cloud)
            gc.assert_called_once_with('artifacts', 'repositories', 'describe', 'mindaam',
                                       '--location=' + cloud.region, missing=True)

    def test_recognized_missing_requires_explicit_opt_in(self):
        for error in [STORAGE_MISSING, 'NOT_FOUND', 'resource was not found',
                      'resource does not exist', 'No URLs matched']:
            with self.subTest(error=error), patch('common.subprocess.run', return_value=self.result(error)):
                self.assertIsNone(command(['unused'], allow_missing=True))
                with self.assertRaises(Blocked):
                    command(['unused'])

    def test_auth_permission_and_network_errors_always_fail(self):
        for error in ['PERMISSION_DENIED', 'Permission denied', '403 Forbidden',
                      '401 Unauthorized', 'UNAUTHENTICATED', 'invalid credentials',
                      'authentication failed', 'reauth required', 'access denied',
                      'network unreachable', 'connection timed out', 'timeout',
                      'DEADLINE_EXCEEDED', 'UNAVAILABLE', 'DNS lookup failed',
                      'name resolution failed', 'SSL certificate error',
                      'TLS handshake failed', 'proxy error', 'transport error']:
            for suffix in ['', '\nNOT_FOUND', '\n' + STORAGE_MISSING]:
                with self.subTest(error=error, suffix=suffix), patch('common.subprocess.run', return_value=self.result(error + suffix)):
                    with self.assertRaises(Blocked):
                        command(['unused'], allow_missing=True)

    def test_unknown_errors_and_bare_404_fail(self):
        for error in ['404', 'HTTP 404 error', 'HTTPError 404: Forbidden', 'HTTPError 4040: Not Found',
                      'HTTPError 404: Not Foundational', 'not found: 4040', 'unexpected error']:
            with self.subTest(error=error), patch('common.subprocess.run', return_value=self.result(error)):
                with self.assertRaises(Blocked):
                    command(['unused'], allow_missing=True)

    def test_bucket_creates_after_real_cli_missing_response(self):
        with patch('common.subprocess.run', side_effect=[self.result(STORAGE_MISSING)] +
                   [subprocess.CompletedProcess([], 0, '{}', '')] * 4) as run:
            bucket(Cloud('mindaam'), 'mindaam-releases')
        self.assertEqual(run.call_args_list[1].args[0][1:4], ['storage', 'buckets', 'create'])
        self.assertEqual(len(run.call_args_list), 5)

    def test_bucket_permission_failure_never_creates(self):
        with patch('common.subprocess.run', return_value=self.result('403 ' + STORAGE_MISSING)) as run:
            with self.assertRaises(Blocked):
                bucket(Cloud('mindaam'), 'mindaam-releases')
        run.assert_called_once()

    def test_unowned_sql_and_secrets_fail_before_reconciliation(self):
        for labels in [{}, {'application': 'other'}]:
            for operation in [lambda c: ensure_postgres(c),
                              lambda c: c.secret('mindaam-postgres-password', generate=lambda: self.fail('regenerated'))]:
                with self.subTest(labels=labels), patch.object(Cloud, 'gc', return_value={'labels': labels}) as gc:
                    with self.assertRaises(Blocked):
                        operation(Cloud('mindaam'))
                    gc.assert_called_once()

    def test_existing_unowned_resources_never_adopted(self):
        for resource in [{}, {'labels': {'application': 'other'}}]:
            cloud = Cloud('mindaam')
            with patch.object(cloud, 'gc', return_value=resource) as gc:
                with self.assertRaises(Blocked):
                    bucket(cloud, 'mindaam-releases')
                gc.assert_called_once()
        cloud = Cloud('mindaam')
        with patch.object(cloud, 'gc', return_value={'description': 'unrelated'}) as gc:
            with self.assertRaises(Blocked):
                ensure(cloud, ['describe'], ['create'], name='network', labels=False)
            gc.assert_called_once()
