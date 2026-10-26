"""Project identity regression tests; all cloud/GitHub calls are mocked."""
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Cloud, Blocked, SETTINGS
from bootstrap import bootstrap


class ProjectValidation(unittest.TestCase):
    def project(self, name='Mindaam', labels=None, state='ACTIVE'):
        return dict(name=name, projectNumber='157480611225',
                    lifecycleState=state, labels=labels or {})

    def test_exact_and_existing_prefixed_ids(self):
        for project in ['mindaam', 'mindaam-production', 'mindaam-staging']:
            self.assertEqual(Cloud(project).project, project)
        for project in ['other-production', 'mindaamother', 'other-mindaam',
                        'Mindaam', 'mindaam-', 'mindaam-a;rm', 'mindaam-production-']:
            with self.subTest(project=project), self.assertRaises(Blocked):
                Cloud(project)

    def test_bootstrap_display_names_remain_scoped(self):
        for project_id, name in [('mindaam', 'Mindaam'), ('mindaam', 'Mindaam Production'),
                                 ('mindaam-staging', 'Mindaam Production')]:
            with self.subTest(project=project_id, name=name):
                cloud = Cloud(project_id)
                with patch.object(cloud, 'gc', side_effect=[self.project(name), {'billingEnabled': True}]):
                    cloud.require_project(bootstrap=True)
                    self.assertEqual(cloud.number, '157480611225')
        for project_id, name in [('mindaam', 'Other'), ('mindaam-staging', 'Mindaam')]:
            cloud = Cloud(project_id)
            with patch.object(cloud, 'gc', return_value=self.project(name)), self.assertRaises(Blocked):
                cloud.require_project(bootstrap=True)

    def test_active_billing_and_post_bootstrap_labels_still_required(self):
        cloud = Cloud('mindaam')
        for project, billing, bootstrap_mode in [
            (self.project(state='DELETE_REQUESTED'), True, True),
            (self.project(), False, True),
            (self.project(), True, False),
            (self.project(labels={'application': 'other'}), True, False),
        ]:
            with patch.object(cloud, 'gc', side_effect=[project, {'billingEnabled': billing}]), self.assertRaises(Blocked):
                cloud.require_project(bootstrap=bootstrap_mode)
        with patch.object(cloud, 'gc', side_effect=[self.project(labels={'application': 'mindaam'}), {'billingEnabled': True}]):
            cloud.require_project()

    def test_bootstrap_95gbp_and_actions_project_wiring(self):
        cloud = Cloud('mindaam')
        def gc(*args, **kwargs):
            if args[:2] == ('projects', 'describe'):
                return self.project()
            if args[:3] == ('billing', 'projects', 'describe'):
                return {'billingEnabled': True, 'billingAccountName': 'billingAccounts/test'}
            if args[:3] == ('billing', 'budgets', 'list'):
                return []
            return None
        def command(args, **kwargs):
            if args[:3] == ['gcloud', 'auth', 'list']:
                return json.dumps([{'account': SETTINGS['owner_email']}])
            if args[:2] == ['gh', 'api']:
                return json.dumps({'id': SETTINGS['repository_id'], 'owner': {'id': SETTINGS['owner_id']}, 'private': True})
            return 'test-token'
        with patch.object(cloud, 'gc', side_effect=gc) as calls, \
             patch('bootstrap.command', side_effect=command) as commands, \
             patch('bootstrap.urlopen', return_value=io.StringIO('{}')), \
             patch('bootstrap.summary'):
            bootstrap(cloud, '95GBP')
        budget = next(call.args for call in calls.call_args_list if call.args[:3] == ('billing', 'budgets', 'create'))
        self.assertIn('--budget-amount=95GBP', budget)
        self.assertIn('--filter-projects=projects/157480611225', budget)
        for key, value in {
            'MINDAAM_PROJECT_ID': 'mindaam',
            'MINDAAM_DEPLOY_SA': 'mindaam-deploy@mindaam.iam.gserviceaccount.com',
            'MINDAAM_WIF_PROVIDER': 'projects/157480611225/locations/global/workloadIdentityPools/mindaam-github/providers/github',
        }.items():
            commands.assert_any_call(['gh', 'variable', 'set', key, '--repo', SETTINGS['repository'], '--body', value])
        root = Path(__file__).resolve().parents[3]
        workflow = (root / '.github/workflows/gcp-deploy.yml').read_text()
        self.assertIn('MINDAAM_PROJECT_ID: ${{ vars.MINDAAM_PROJECT_ID }}', workflow)
        self.assertIn("Cloud(os.environ['MINDAAM_PROJECT_ID'])", (root / 'infrastructure/gcp/workflow.py').read_text())
