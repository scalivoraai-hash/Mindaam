import copy,datetime,os,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Blocked
from release_policy import BETA,POLICY,profile,required_checks,validate_beta,evidence_name,review_name
from render import service
from test_deployment import FakeCloud
import review

class BetaPolicy(unittest.TestCase):
 def test_blocked_draft_is_not_release_approval(self):
  c=FakeCloud();sha='a'*40
  c.objects[f'releases/{sha}/staging.json']={'sha':sha,'image':'test-image','profile':BETA}
  c.objects[f'releases/{sha}/metrics.json']={'series':{'test-only-memory':.95}}
  before=copy.deepcopy(c.objects)
  with patch.dict(os.environ,{'RELEASE_PROFILE':BETA}),patch('review.inventory',return_value={'test_only':True}),patch('review.optional_secrets',return_value={}):
   draft=review.packet(c,sha)
   self.assertFalse(draft['staging_acceptance_verified']);self.assertFalse(draft['owner_approved'])
   self.assertTrue(draft['readiness'].startswith('BLOCKED'))
   self.assertEqual(draft['resource_measurements'],c.objects[f'releases/{sha}/metrics.json'])
   self.assertEqual(c.objects,before)
   with self.assertRaises(Blocked):review.save(c,sha,draft)
   del c.objects[f'releases/{sha}/metrics.json']
   with self.assertRaises(Blocked):review.packet(c,sha)
 def evidence(self):return {'profile':BETA,'deferred':POLICY['deferred'],'checks':dict.fromkeys(required_checks(BETA),True)}
 def test_deferred_never_becomes_pass(self):
  value=self.evidence();validate_beta(value)
  for key in POLICY['deferred']:
   altered=copy.deepcopy(value);altered['checks'][key]=True
   with self.assertRaises(Blocked):validate_beta(altered)
 def test_every_nonpayment_check_remains_mandatory(self):
  for key in required_checks(BETA):
   value=self.evidence();value['checks'][key]=False
   with self.assertRaises(Blocked):validate_beta(value)
 def test_full_path_and_beta_evidence_are_separate(self):
  self.assertIn('venue_booking',required_checks('full'))
  self.assertNotEqual(evidence_name(BETA),evidence_name('full'))
  self.assertNotEqual(review_name(BETA),review_name('full'))
 def test_no_unreviewed_beta_promotion(self):
  with self.assertRaises(Blocked):validate_beta(self.evidence(),{'profile':BETA,'deferred':POLICY['deferred'],'payment_actions_enabled':False})
 def test_gate_both_deployment_environments(self):
  with patch.dict(os.environ,{'RELEASE_PROFILE':BETA}):
   for env in ['staging','production']:
    result=service(FakeCloud(),env,'image','https://example.run.app')
    values={x['name']:x.get('value') for x in result['spec']['template']['spec']['containers'][0]['env']}
    self.assertEqual(values['MINDAAM_PAYMENT_ACTIONS_ENABLED'],'false')
 def test_unknown_profile_fails_closed(self):
  with patch.dict(os.environ,{'RELEASE_PROFILE':'skip-everything'}):
   with self.assertRaises(Blocked):profile()
 def test_beta_policy_expires(self):
  expired=datetime.date(2027,1,1); end=datetime.date(2026,11,28)
  with patch.dict(os.environ,{'RELEASE_PROFILE':BETA}),patch('release_policy.datetime.date') as date:
   date.today.return_value=expired
   date.fromisoformat.return_value=end
   with self.assertRaises(Blocked):profile()
