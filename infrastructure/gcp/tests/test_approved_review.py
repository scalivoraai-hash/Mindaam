import sys,unittest,time
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from approved_review import finalise
from recovery import SHA
from common import Blocked
class ApprovalSafety(unittest.TestCase):
 def test_cannot_reuse_owner_approval_for_other_release(self):
  c=Mock()
  with self.assertRaises(Blocked):finalise(c,'a'*40)
  c.put_json.assert_not_called()
 def test_absent_approval_does_not_publish(self):
  c=Mock();c.get_json.return_value=None
  with self.assertRaises(Blocked):finalise(c,SHA)
  c.put_json.assert_not_called()
 def test_failed_or_unremoved_restore_cannot_publish(self):
  for status,clean in [('FAIL',True),('PASS',False)]:
   c=Mock();e={'sha':SHA,'image':'digest','status':status,'cleanup':clean,'completed_at':time.time()}
   c.get_json.side_effect=[{'sha':SHA,'image':'digest'},{'owner_approved':True},e,e]
   with self.assertRaises(Blocked):finalise(c,SHA)
   c.put_json.assert_not_called()
