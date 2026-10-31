import copy,json,os,sys,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from release_candidate import selected,fresh
from common import Blocked
from release_policy import BETA,required_checks
class CandidateSafety(unittest.TestCase):
 def setUp(self):
  self.intent=json.loads((Path(__file__).resolve().parents[1]/'release-preparation.json').read_text())
  self.sha=self.intent['sha'];self.image=self.intent['image'];self.c=Mock(project='mindaam',region='europe-west2')
  self.e={'sha':self.sha,'image':self.image,'revision':'r1','profile':BETA,'checks':dict.fromkeys(required_checks(BETA),True)}
  self.c.get_json.return_value=self.e
  self.service={'status':{'latestReadyRevisionName':'r1'},'spec':{'template':{'spec':{'containers':[{'image':self.image}]}}}}
 def test_exact_accepted_image(self):
  with patch.dict(os.environ,RELEASE_PROFILE=BETA),patch('release_candidate.ready_service',return_value=self.service):self.assertEqual(selected(self.c,self.sha),self.e)
 def test_mismatch_or_incomplete_never_accesses_service(self):
  for field,value in [('image',self.image[:-1]+'0'),('sha','f'*40),('checks',{})]:
   self.c.get_json.return_value={**self.e,field:value}
   with patch.dict(os.environ,RELEASE_PROFILE=BETA),patch('release_candidate.ready_service') as service:
    with self.assertRaises(Blocked):selected(self.c,self.sha)
    service.assert_not_called()
 def test_current_revision_drift(self):
  service=copy.deepcopy(self.service);service['status']['latestReadyRevisionName']='r2'
  with patch.dict(os.environ,RELEASE_PROFILE=BETA),patch('release_candidate.ready_service',return_value=service):
   with self.assertRaises(Blocked):selected(self.c,self.sha)
 def test_freshness_and_cleanup(self):
  e={'sha':self.sha,'image':self.image,'status':'PASS','cleanup':True,'completed_at':time.time()}
  self.assertTrue(fresh(e,self.sha,self.image))
  for key,value in [('cleanup',False),('status','FAIL'),('sha','a'*40),('image','other'),('completed_at',time.time()-86401),('completed_at',time.time()+100)]:self.assertFalse(fresh({**e,key:value},self.sha,self.image))
 def test_security_never_bootstraps_or_migrates(self):
  import security_verify,inspect
  source=inspect.getsource(security_verify)
  for forbidden in ('bootstrap_owner','SUPER_ADMIN_INITIAL_PASSWORD','migrate(c,','owner-cost-approval.json'):self.assertNotIn(forbidden,source)
 def test_finalise_requires_authenticated_owner_even_with_approval(self):
  from approved_review import finalise
  c=Mock();c.verified_owner_principal=None;c.get_json.return_value={'sha':self.sha,'image':self.image,'principal':'sain@scalivora.com','owner_approved':True,'approved_at':time.time()}
  with patch('approved_review.prepare',return_value={'image':self.image}):
   with self.assertRaises(Blocked):finalise(c,self.sha)
  c.put_json.assert_not_called()
 def test_finalise_rejects_different_image_approval(self):
  from approved_review import finalise
  c=Mock();c.get_json.return_value={'sha':self.sha,'image':'other','principal':'sain@scalivora.com','owner_approved':True,'approved_at':time.time()}
  with patch('approved_review.prepare',return_value={'image':self.image}):
   with self.assertRaises(Blocked):finalise(c,self.sha)
  c.put_json.assert_not_called()
