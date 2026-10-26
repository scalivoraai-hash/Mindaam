"""First-deployment discovery regressions; never contact Google Cloud."""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Blocked, Cloud, command
from deploy import bucket, ensure

STORAGE_MISSING = 'ERROR: (gcloud.storage.buckets.describe) gs://mindaam-releases not found: 404.'


class MissingResources(unittest.TestCase):
    def result(self, error):
        return subprocess.CompletedProcess([], 1, '', error)

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
