"""Owner-operated HTTPS login evidence. Never resets credentials or approves a release."""
import argparse,getpass,http.cookiejar,json,os,time
from urllib.request import build_opener,HTTPCookieProcessor,Request,urlopen
from urllib.error import HTTPError
from common import Blocked,command
from owner_recover import OwnerCloud,OWNER,verified_owner
from release_candidate import selected
from readiness import ready_service

def verify(origin):
 jar=http.cookiejar.CookieJar();client=build_opener(HTTPCookieProcessor(jar))
 def call(path,data=None):
  req=Request(origin+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':origin,'X-Pulse-Client':'web'})
  try:
   with client.open(req,timeout=30) as res:return res.status,json.load(res)
  except HTTPError as e:return e.code,{}
 if call('/api/super-admin/overview')[0]!=401:raise Blocked('Anonymous admin access check failed')
 password=getpass.getpass('Existing owner password for '+origin+': ')
 try:status,body=call('/api/auth/admin-login',{'identifier':OWNER,'password':password})
 finally:del password
 if status!=200:raise Blocked('Owner login rejected; no reset performed')
 try:
  u=body.get('user',{})
  if u.get('email')!=OWNER or u.get('username')!='mindaam_owner' or u.get('role')!='super_admin' or u.get('must_change_password'):raise Blocked('Authenticated owner identity or setup mismatch')
  cookies=[x for x in jar if x.name=='pulse-session']
  if len(cookies)!=1 or not cookies[0].secure or not cookies[0].has_nonstandard_attr('HttpOnly') or str(cookies[0].get_nonstandard_attr('SameSite','')).lower()!='lax':raise Blocked('Session cookie protections missing')
  if call('/api/super-admin/overview')[0]!=200 or call('/api/me')[0]!=200:raise Blocked('Authenticated dashboard/session check failed')
 finally:
  logout=call('/api/auth/logout',{})[0]
 if logout!=200 or call('/api/super-admin/overview')[0]!=401:raise Blocked('Logout invalidation failed')
 return {'owner_login':True,'dashboard':True,'secure_cookie':True,'logout':True,'owner_identity':OWNER}

def run(sha,approve=False):
 if os.getenv('CI') or os.getenv('GITHUB_ACTIONS'):raise Blocked('Run privately in owner Cloud Shell')
 access=command(['gcloud','auth','print-access-token','--account='+OWNER],sensitive=True)
 try:
  with urlopen(Request('https://www.googleapis.com/oauth2/v2/userinfo',headers={'Authorization':'Bearer '+access}),timeout=20) as response:verified_owner(json.load(response))
 finally:del access
 class OwnerReleaseCloud(OwnerCloud):
  verified_owner_principal=OWNER
  def put_json(self,key,value):
   import tempfile
   with tempfile.NamedTemporaryFile(mode='w') as f:
    os.chmod(f.name,0o600);json.dump(value,f);f.flush()
    command(['gcloud','storage','cp',f.name,f'gs://{self.bucket}/{key}','--account='+OWNER,'--project=mindaam'],sensitive=True)
 c=OwnerReleaseCloud('mindaam');c.require_project();release=selected(c,sha)
 if approve:
  from approved_review import prepare,finalise
  review=prepare(c,sha)
  print('Approve production limited beta:',sha,release['image'],'Payments remain disabled. Idle $48.76 / light $91.98 monthly.')
  if input('Type the full image digest to approve: ').strip()!=release['image'].split('@')[1]:raise Blocked('Approval not confirmed')
  c.put_json(f'releases/{sha}/owner-release-approval.json',{'sha':sha,'image':release['image'],'principal':OWNER,'owner_approved':True,'approved_at':time.time()})
  finalise(c,sha);return
 result={'sha':sha,'image':release['image'],'principal':OWNER,'status':'PASS','environments':{}}
 for env,origin in [('staging',release['origin']),('production','https://mindaam.com')]:
  service=ready_service(c,'mindaam-'+env)
  checks=verify(origin)
  checks.update(revision=service['status']['latestReadyRevisionName'],image=service['spec']['template']['spec']['containers'][0]['image'])
  result['environments'][env]=checks
 result['completed_at']=time.time()
 # OwnerCloud inherits put_json, so explicitly force the authenticated account for the write.
 import tempfile
 with tempfile.NamedTemporaryFile(mode='w') as f:
  os.chmod(f.name,0o600);json.dump(result,f);f.flush()
  command(['gcloud','storage','cp',f.name,f'gs://{c.bucket}/releases/{sha}/owner-access.json','--account='+OWNER,'--project=mindaam'],sensitive=True)
 print('Both owner logins, dashboard access and logout verified. No credentials saved. Production approval remains separate.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--release-sha',required=True);p.add_argument('--approve',action='store_true');a=p.parse_args()
 try:run(a.release_sha,a.approve)
 except Exception:raise SystemExit('Owner access verification stopped; no credentials printed or changed.') from None
