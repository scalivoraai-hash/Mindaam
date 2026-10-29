import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from recovery import target,guard
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
