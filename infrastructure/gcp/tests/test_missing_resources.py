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
from deploy import bucket, ensure, foundation, DESCRIPTION
from common import SETTINGS

STORAGE_MISSING = 'ERROR: (gcloud.storage.buckets.describe) gs://mindaam-releases not found: 404.'
IDENTITY = (' This command is authenticated as mindaam-deploy@mindaam.iam.gserviceaccount.com'
            ' using the credentials ...')
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
                           f"The resource '{resource}' was not found"]:
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
                  'name resolution failed', 'proxy error', 'transport error']
        for cli, resource in DISCOVERY:
            for error in errors:
                for message in [error + '\nNOT_FOUND' + IDENTITY,
                                'NOT_FOUND' + IDENTITY + '\n' + error,
                                'NOT_FOUND' + IDENTITY + ' ' + error]:
                    with self.subTest(cli=cli, error=error, message=message), patch(
                        'common.subprocess.run', return_value=self.result(
                            f'ERROR: (gcloud.{cli}) {resource}: {message}')):
                        with self.assertRaises(Blocked):
                            Cloud('mindaam').gc(*cli.split('.'), resource, missing=True)

    def test_first_foundation_creates_all_missing_resources(self):
        created, missing = set(), set()
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
            data = {}
            if args[:2] == ['projects', 'describe']:
                data = {'lifecycleState': 'ACTIVE', 'projectNumber': '157480611225',
                        'labels': {'application': 'mindaam'}}
            elif args[:3] == ['billing', 'projects', 'describe']:
                data = {'billingEnabled': True}
            elif args[:2] == ['auth', 'print-access-token'] or args[:3] == ['secrets', 'versions', 'access']:
                return subprocess.CompletedProcess([], 0, 'test-only-value', '')
            elif 'create' in args:
                i = args.index('create'); created.add(tuple(args[:i] + [args[i + 1]]))
            elif 'describe' in args:
                i = args.index('describe'); key = tuple(args[:i] + [args[i + 1]])
                if key not in created:
                    missing.add(key)
                    return self.result(f'ERROR: (gcloud.{".".join(args[:i + 1])}) '
                                       f'NOT_FOUND: {key} was not found.' + IDENTITY)
                data = dict(resource)
                if args[:2] == ['compute', 'firewall-rules']:
                    private = key[-1] == 'mindaam-redis-private'
                    data.update(allowed=([{'IPProtocol': 'tcp', 'ports': ['6379']}] if private else
                        [{'IPProtocol': 'tcp', 'ports': ['80', '443', '7881']},
                         {'IPProtocol': 'udp', 'ports': ['3478', '50000-50200']}]),
                        sourceRanges=[SETTINGS['subnet_cidr'] if private else '0.0.0.0/0'],
                        targetServiceAccounts=[Cloud('mindaam').sa('media')], direction='INGRESS')
            elif 'list' in args:
                data = []
            elif args[:2] == ['storage', 'cat']:
                missing.add(('storage', 'cat', args[2]))
                return self.result('No URLs matched: ' + args[2] + IDENTITY)
            return subprocess.CompletedProcess([], 0, json.dumps(data), '')

        def sql_create(*args, **kwargs):
            created.add(('sql', 'instances', 'mindaam-postgres'))
            return io.StringIO('{"name": "test-operation"}')

        with patch('common.subprocess.run', side_effect=run), \
             patch('deploy.urlopen', side_effect=sql_create), \
             patch.dict('os.environ', {'MINDAAM_BUDGET_CONFIRMED': 'true'}), \
             patch('deploy.summary'):
            foundation(Cloud('mindaam'))
        self.assertEqual(missing - {('storage', 'cat', 'gs://mindaam-releases/vm/current.json')}, created)
        for cli, name in DISCOVERY:
            parts = cli.split('.')
            key = tuple(parts[:-1] + [name]) if parts[-1] == 'describe' else tuple(parts + [name])
            if cli == 'compute.networks.describe':
                key = ('compute', 'networks', 'mindaam')
            self.assertIn(key, missing)

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
        for error in ['404', 'HTTP 404 error', 'not found: 4040', 'unexpected error']:
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
