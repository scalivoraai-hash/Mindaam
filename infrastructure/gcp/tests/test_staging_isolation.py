import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from staging_isolation import fingerprint


class StagingIsolationTests(unittest.TestCase):
    def test_revision_image_and_traffic_changes_are_detectable(self):
        service = {'metadata': {'name': 'mindaam-production'}, 'status': {
            'latestReadyRevisionName': 'prod-1', 'latestCreatedRevisionName': 'prod-1',
            'traffic': [{'revisionName': 'prod-1', 'percent': 100}]}}
        revision = {'status': {'imageDigest': 'sha256:a'}}
        original = fingerprint(service, revision)
        service['status']['traffic'][0]['percent'] = 50
        self.assertNotEqual(original, fingerprint(service, revision))
        service['status']['traffic'][0]['percent'] = 100
        revision['status']['imageDigest'] = 'sha256:b'
        self.assertNotEqual(original, fingerprint(service, revision))
        revision['status']['imageDigest'] = 'sha256:a'
        service['status']['latestCreatedRevisionName'] = 'prod-2'
        self.assertNotEqual(original, fingerprint(service, revision))
