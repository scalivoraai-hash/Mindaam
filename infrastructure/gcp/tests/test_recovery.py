import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from recovery import target,guard,run,RECOVERY_SHA
from common import Blocked
class RecoverySafety(unittest.TestCase):
 def test_cannot_target_live_database(self):
  for value in ['mindaam-postgres','../production','1;rm','']:
   with self.assertRaises(Blocked):target(value,'1')
 def test_rejects_unowned_cleanup(self):
  name=target('123','1')
  with self.assertRaises(Blocked):guard({'name':name,'settings':{'userLabels':{'application':'mindaam','recovery_run':'456'}}},name,'123')
  with self.assertRaises(Blocked):guard({'name':'mindaam-postgres'},'mindaam-postgres','123')
 def test_accepts_only_invocation_target(self):
  name=target('123','1');guard({'name':name,'settings':{'userLabels':{'application':'mindaam','recovery_run':'123'}}},name,'123')

 def test_unreviewed_drill_target_cannot_read_or_create_cloud_resources(self):
  from unittest.mock import Mock
  cloud=Mock(project='mindaam')
  with self.assertRaisesRegex(Blocked,'exact Mindaam release'):run(cloud,'0'*40)
  cloud.get_json.assert_not_called();cloud.gc.assert_not_called()
 def test_scoped_drill_still_requires_actual_verified_release(self):
  from unittest.mock import Mock
  cloud=Mock(project='mindaam');cloud.get_json.return_value=None
  with self.assertRaisesRegex(Blocked,'Verified release required'):run(cloud,RECOVERY_SHA)
  cloud.gc.assert_not_called()
 def test_other_project_rejected_before_any_resource_access(self):
  from unittest.mock import Mock
  cloud=Mock(project='other')
  with self.assertRaises(Blocked):run(cloud,RECOVERY_SHA)
  cloud.get_json.assert_not_called();cloud.gc.assert_not_called()
