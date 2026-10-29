import copy,datetime,os,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import resource_resume as r
from common import Blocked
class ResourceResume(unittest.TestCase):
 def fixture(self):
  run={'id':r.RUN,'head_sha':r.HEAD,'head_branch':'main','repository':{'full_name':r.REPO},'path':'.github/workflows/gcp-deploy.yml','event':'workflow_dispatch','status':'completed','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  artifact={'id':r.ARTIFACT,'workflow_run':{'id':r.RUN},'expired':False,'digest':'sha256:'+r.DIGEST}
  release={'sha':r.SHA,'profile':'limited-public-beta-v1','revision':'mindaam-staging-00009-f8l'}
  return run,artifact,release
 def test_exact_proof_only_and_expiry(self):
  with patch.dict(os.environ,{'RELEASE_SHA':r.SHA}):
   r.validate_proof(*self.fixture())
   for index,key,value in [(0,'head_sha','other'),(0,'event','pull_request'),(0,'created_at','2020-01-01T00:00:00Z'),(1,'digest','sha256:other'),(1,'expired',True),(2,'sha','other'),(2,'revision','different')]:
    args=list(self.fixture());args[index][key]=value
    with self.assertRaises(Blocked):r.validate_proof(*args)
  with patch.dict(os.environ,{'RELEASE_SHA':'other'}):
   with self.assertRaises(Blocked):r.validate_proof(*self.fixture())
