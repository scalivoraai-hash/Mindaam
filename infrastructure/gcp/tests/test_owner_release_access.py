import io,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError,URLError
from http.cookiejar import Cookie
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import owner_release_access as m

SECRET='SENSITIVE_SENTINEL_DO_NOT_PRINT'
class Response(io.BytesIO):
 status=200
 def __enter__(self):return self
 def __exit__(self,*a):self.close()

class OwnerDiagnostics(unittest.TestCase):
 def exercise(self,env='staging',failure=None,body=None,cookie=True):
  requests=[]
  def opener(processor):
   jar=processor.cookiejar
   class Client:
    def open(self,req,timeout):
     path=req.full_url.split('.test')[-1];requests.append(path)
     index=len(requests)
     if failure and index==failure[0]:raise failure[1]
     if index in (1,6):raise HTTPError(req.full_url,401,SECRET,{},io.BytesIO(SECRET.encode()))
     if index==2:
      if cookie:jar.set_cookie(Cookie(0,'pulse-session',SECRET,None,False,'example.test',False,False,'/',True,True,None,True,None,None,{'HttpOnly':None,'SameSite':'lax'},False))
      value=body if body is not None else {'user':{'email':m.OWNER,'username':'mindaam_owner','role':'super_admin','must_change_password':False}}
     else:value={'ok':True}
     return Response(json.dumps(value).encode())
   return Client()
  with patch.object(m,'build_opener',side_effect=opener),patch.object(m.getpass,'getpass',return_value=SECRET):
   try:return m.verify('https://example.test',env),requests
   except m.Diagnostic as e:
    self.assertNotIn(SECRET,str(e));return e,requests
 def test_success_both_environments(self):
  for env in ('staging','production'):
   result,requests=self.exercise(env);self.assertTrue(result['logout']);self.assertEqual(len(requests),6)
 def test_login_http_categories(self):
  for status in (400,401,403,429,503):
   e,_=self.exercise('production',(2,HTTPError(SECRET,status,SECRET,{},None)))
   self.assertEqual((e.stage,e.category),('production.login','http_'+str(status)))
 def test_dashboard_session_logout(self):
  for index,label in ((3,'dashboard'),(4,'session'),(5,'logout'),(6,'logout_validation')):
   e,requests=self.exercise(failure=(index,HTTPError(SECRET,503,SECRET,{},None)))
   self.assertEqual(e.stage,'staging.'+label)
   if index in (3,4):self.assertIn('/api/auth/logout',requests)
 def test_cookie_and_identity_fail_closed(self):
  e,requests=self.exercise(cookie=False);self.assertEqual(e.category,'session_cookie_count');self.assertIn('/api/auth/logout',requests)
  for body,category in (([], 'response_shape'),({'user':{}},'owner_mismatch')):
   e,_=self.exercise(body=body);self.assertEqual(e.category,category)
 def test_transport_failure_categories(self):
  for error,category in ((TimeoutError(SECRET),'timeout'),(URLError(SECRET),'network_error'),(json.JSONDecodeError(SECRET,SECRET,0),'invalid_json')):
   e,_=self.exercise(failure=(2,error));self.assertEqual(e.category,category)
 def test_no_raw_exception_text(self):
  for error,category in ((m.Blocked(SECRET),'gate_rejected'),(RuntimeError(SECRET),'unexpected_error'),(EOFError(SECRET),'input_cancelled')):
   with self.assertRaises(m.Diagnostic) as caught:
    with m.stage('release_evidence'):raise error
   self.assertEqual(caught.exception.category,category);self.assertNotIn(SECRET,str(caught.exception))
 def test_primary_failure_survives_cleanup_failure(self):
  e,_=self.exercise(body={'user':{}},failure=(3,HTTPError(SECRET,503,SECRET,{},None)))
  self.assertEqual(e.category,'owner_mismatch')
