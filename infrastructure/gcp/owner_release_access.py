"""Owner-operated HTTPS login evidence. Never resets credentials or approves a release."""
import argparse,getpass,http.cookiejar,json,os,time
from urllib.request import build_opener,HTTPCookieProcessor,Request,urlopen
from urllib.error import HTTPError,URLError
import ssl,socket
from contextlib import contextmanager
from common import Blocked,command
from owner_recover import OwnerCloud,OWNER,verified_owner
from release_candidate import selected
from readiness import ready_service
from owner_feature_checks import verify as verify_feature_reads

class Diagnostic(Blocked):
 """Only locally defined stage/category labels may reach the terminal."""
 def __init__(self,stage,category):
  self.stage,self.category=stage,category
  super().__init__('Owner verification failed: stage='+stage+' category='+category+'. No credentials printed or changed.')

@contextmanager
def stage(name):
 try:yield
 except Diagnostic:raise
 except HTTPError as e:raise Diagnostic(name,'http_'+str(int(e.code))) from None
 except (TimeoutError,socket.timeout):raise Diagnostic(name,'timeout') from None
 except ssl.SSLError:raise Diagnostic(name,'tls_error') from None
 except URLError:raise Diagnostic(name,'network_error') from None
 except (json.JSONDecodeError,UnicodeError):raise Diagnostic(name,'invalid_json') from None
 except Blocked:raise Diagnostic(name,'gate_rejected') from None
 except (EOFError,KeyboardInterrupt):raise Diagnostic(name,'input_cancelled') from None
 except Exception:raise Diagnostic(name,'unexpected_error') from None

def require(name,condition,category):
 if not condition:raise Diagnostic(name,category)

def verify(origin,environment='staging',verify_features=False):
 # Labels are local constants, never remote response text or URLs.
 require('environment',environment in ('staging','production'),'invalid_environment')
 prefix=environment+'.'
 jar=http.cookiejar.CookieJar();client=build_opener(HTTPCookieProcessor(jar))
 def call(label,path,expected,data=None,read_json=False):
  with stage(prefix+label):
   req=Request(origin+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':origin,'X-Pulse-Client':'web'})
   try:
    with client.open(req,timeout=30) as res:
     require(prefix+label,res.status==expected,'http_'+str(int(res.status)))
     return json.load(res) if read_json else {}
   except HTTPError as e:
    if e.code==expected:return {}
    raise
 call('anonymous_admin','/api/super-admin/overview',401)
 with stage(prefix+'password_input'):
  password=getpass.getpass('Existing owner password for '+origin+': ')
 try:
  body=call('login','/api/auth/admin-login',200,{'identifier':OWNER,'password':password},True)
 finally:del password
 failure=None;feature_evidence={}
 try:
  with stage(prefix+'identity'):
   require(prefix+'identity',isinstance(body,dict) and isinstance(body.get('user'),dict),'response_shape')
   u=body['user']
   require(prefix+'identity',u.get('email')==OWNER and u.get('username')=='mindaam_owner' and u.get('role')=='super_admin','owner_mismatch')
   require(prefix+'identity',u.get('must_change_password') is False,'password_setup_required')
  with stage(prefix+'cookie'):
   cookies=[x for x in jar if x.name=='pulse-session']
   require(prefix+'cookie',len(cookies)==1,'session_cookie_count')
   require(prefix+'cookie',cookies[0].secure,'secure_missing')
   require(prefix+'cookie',cookies[0].has_nonstandard_attr('HttpOnly'),'httponly_missing')
   require(prefix+'cookie',str(cookies[0].get_nonstandard_attr('SameSite','')).lower()=='lax','samesite_invalid')
  call('dashboard','/api/super-admin/overview',200)
  call('session','/api/me',200)
  if verify_features:
   with stage(prefix+'feature_reads'):
    require(prefix+'feature_reads',environment=='staging','staging_only')
    feature_evidence=verify_feature_reads(call,u['id'])
 except Diagnostic as e:failure=e
 finally:
  try:call('logout','/api/auth/logout',200,{})
  except Diagnostic as e:
   if failure is None:failure=e
 if failure:raise failure
 call('logout_validation','/api/super-admin/overview',401)
 return {'owner_login':True,'dashboard':True,'secure_cookie':True,'logout':True,'owner_identity':OWNER,**feature_evidence}

def run(sha,approve=False):
 if os.getenv('CI') or os.getenv('GITHUB_ACTIONS'):raise Blocked('Run privately in owner Cloud Shell')
 with stage('google_credentials'):
  access=command(['gcloud','auth','print-access-token','--account='+OWNER],sensitive=True)
 try:
  with stage('google_identity'),urlopen(Request('https://www.googleapis.com/oauth2/v2/userinfo',headers={'Authorization':'Bearer '+access}),timeout=20) as response:verified_owner(json.load(response))
 finally:del access
 class OwnerReleaseCloud(OwnerCloud):
  verified_owner_principal=OWNER
  def put_json(self,key,value):
   import tempfile
   with tempfile.NamedTemporaryFile(mode='w') as f:
    os.chmod(f.name,0o600);json.dump(value,f);f.flush()
    command(['gcloud','storage','cp',f.name,f'gs://{self.bucket}/{key}','--account='+OWNER,'--project=mindaam'],sensitive=True)
 with stage('project_access'):
  c=OwnerReleaseCloud('mindaam');c.require_project()
 with stage('release_profile'):
  from release_policy import profile
  profile()
 with stage('release_evidence'):
  release=selected(c,sha)
 if approve:
  from approved_review import prepare,finalise
  with stage('approval_evidence'):review=prepare(c,sha)
  print('Approve production limited beta:',sha,release['image'],'Payments remain disabled. Idle $48.76 / light $91.98 monthly.')
  if input('Type the full image digest to approve: ').strip()!=release['image'].split('@')[1]:raise Blocked('Approval not confirmed')
  with stage('approval_write'):c.put_json(f'releases/{sha}/owner-release-approval.json',{'sha':sha,'image':release['image'],'principal':OWNER,'owner_approved':True,'approved_at':time.time()})
  with stage('approval_finalize'):finalise(c,sha)
  return
 result={'sha':sha,'image':release['image'],'principal':OWNER,'status':'PASS','environments':{}}
 for env,origin in [('staging',release['origin']),('production','https://mindaam.com')]:
  with stage(env+'.service_readiness'):service=ready_service(c,'mindaam-'+env)
  checks=verify(origin,env,verify_features=env=='staging')
  checks.update(revision=service['status']['latestReadyRevisionName'],image=service['spec']['template']['spec']['containers'][0]['image'])
  result['environments'][env]=checks
 result['completed_at']=time.time()
 with stage('owner_evidence_write'):
  c.put_json(f'releases/{sha}/owner-access.json',result)
 print('Both owner logins, dashboard access and logout verified. No credentials saved. Production approval remains separate.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--release-sha',required=True);p.add_argument('--approve',action='store_true');a=p.parse_args()
 try:
  with stage('preflight'):run(a.release_sha,a.approve)
 except Diagnostic as e:raise SystemExit(str(e)) from None
