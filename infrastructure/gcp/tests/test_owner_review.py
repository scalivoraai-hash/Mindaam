import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from owner_review import PROBE,run
from common import Blocked
class OwnerReviewSafety(unittest.TestCase):
 def test_probe_is_read_only_and_never_exports_a_secret(self):
  compile(PROBE,'owner-review','exec')
  self.assertIn('SET TRANSACTION READ ONLY',PROBE)
  self.assertIn("('mindaam_staging','mindaam_staging')",PROBE)
  for forbidden in ('bootstrap_owner','hash_password(','UPDATE users','INSERT INTO','client.post','result.update(owner)'):
   self.assertNotIn(forbidden,PROBE)
  self.assertIn("'initial_credential_matches':bool",PROBE)
 def test_wrong_project_is_blocked_before_access(self):
  class Cloud:project='unrelated'
  with self.assertRaises(Blocked):run(Cloud(),'a'*40)
