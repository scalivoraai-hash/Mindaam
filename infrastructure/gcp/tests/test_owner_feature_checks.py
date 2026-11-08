import copy,sys,unittest,io,json
from unittest.mock import patch
from http.cookiejar import Cookie
from urllib.error import HTTPError
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Blocked
from owner_feature_checks import verify,require_evidence,REQUIRED
import owner_release_access as owner

USER='11111111-1111-4111-8111-111111111111'

class OwnerFeatures(unittest.TestCase):
 def responses(self):
  result={
   'movement_settings':{'bounds':{'walk':[.5,100],'run':[1,100]},'speeds':{'walk':4,'run':8}},
   'property_coverage':[{'city':'installed-city','eligible':12,'registered':12}],
   'property_economy':{'registered':12,'available':9,'owned':3,'owners':2,'claims_xp':6000,'resales_xp':2400,'pending':1},
   'user_directory':{'items':[{'id':USER,'email':'private@example.test'}]},
   'user_overview':{'user':{'id':USER},'tab':'overview','kpis':dict.fromkeys(('Spendable XP','Pulse Credits','Owned properties','Hosted events','Active days'),0)},
  }
  for tab in ('wallet','properties','events','activity'):
   result['user_'+tab]={'user':{'id':USER},'tab':tab,'items':[],'total':0}
  result['user_wallet'].update(xp=25,credits=10,purchased_available=5)
  return result
 def check(self,responses):
  calls=[]
  def call(label,path,status,data=None,read_json=False):
   self.assertIsNone(data);self.assertTrue(read_json);self.assertEqual(status,200)
   calls.append(path);return responses[label]
  return verify(call,USER),calls
 def test_read_only_checks_export_only_boolean_evidence(self):
  rows=self.responses();before=copy.deepcopy(rows);result,calls=self.check(rows)
  self.assertEqual(result,dict.fromkeys(REQUIRED,True));self.assertEqual(rows,before)
  self.assertEqual(len(calls),9);self.assertNotIn('private@example.test',str(result))
  self.assertTrue(all('/admin/' in p or '/super-admin/' in p for p in calls))
 def test_inventory_gap_wrong_totals_and_missing_admin_fields_fail(self):
  for mutate in [
   lambda r:r['property_coverage'][0].update(registered=11),
   lambda r:r['property_economy'].update(available=12),
   lambda r:r['movement_settings']['bounds'].update(walk=[.5,8]),
   lambda r:r['user_overview']['kpis'].pop('Owned properties'),
   lambda r:r['user_wallet'].pop('purchased_available'),
   lambda r:r['user_properties'].update(user={'id':'another-account'}),
  ]:
   with self.subTest(mutation=mutate):
    rows=self.responses();mutate(rows)
    with self.assertRaises(Blocked):self.check(rows)
 def test_old_owner_access_cannot_satisfy_new_feature_acceptance(self):
  require_evidence(dict.fromkeys(REQUIRED,True))
  for key in REQUIRED:
   evidence=dict.fromkeys(REQUIRED,True);evidence.pop(key)
   with self.assertRaises(Blocked):require_evidence(evidence)
 def feature_flow(self,failure=False):
  paths=[]
  class Response(io.BytesIO):
   status=200
   def __enter__(self):return self
   def __exit__(self,*_):self.close()
  def opener(processor):
   class Client:
    def open(self,req,timeout):
     path=req.full_url.split('example.test')[-1];paths.append(path)
     if len(paths) in (1,6):raise HTTPError(req.full_url,401,'private',{},None)
     if path=='/api/auth/admin-login':
      processor.cookiejar.set_cookie(Cookie(0,'pulse-session','private',None,False,'example.test',False,False,'/',True,True,None,True,None,None,{'HttpOnly':None,'SameSite':'lax'},False))
      value={'user':{'id':USER,'email':owner.OWNER,'username':'mindaam_owner','role':'super_admin','must_change_password':False}}
     else:value={}
     return Response(json.dumps(value).encode())
   return Client()
  with patch.object(owner,'build_opener',side_effect=opener),patch.object(owner.getpass,'getpass',return_value='private'),patch.object(owner,'verify_feature_reads',return_value=dict.fromkeys(REQUIRED,True),side_effect=Blocked('private') if failure else None) as feature:
   if failure:
    with self.assertRaises(owner.Diagnostic) as caught:owner.verify('https://example.test','staging',verify_features=True)
    self.assertEqual(caught.exception.stage,'staging.feature_reads');self.assertNotIn('private',str(caught.exception))
    self.assertIn('/api/auth/logout',paths)
   else:
    result=owner.verify('https://example.test','staging',verify_features=True)
    require_evidence(result);self.assertTrue(result['logout'])
   feature.assert_called_once()
 def test_authenticated_feature_evidence_is_returned_after_logout(self):self.feature_flow()
 def test_feature_failure_logs_owner_out_and_does_not_export_details(self):self.feature_flow(True)
