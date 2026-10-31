"""Read-only existing staging owner recovery evidence; never resets credentials."""
import base64,json,time
from pathlib import Path
from common import Blocked
from readiness import ready_service

PROBE='''import os,json
os.environ['DATABASE_URL']=os.environ['RUNTIME_DATABASE_URL']
from backend.api.db import SessionLocal
from backend.api.auth import check_password
from sqlalchemy import text
with SessionLocal.begin() as db:
 db.execute(text('SET TRANSACTION READ ONLY'))
 assert tuple(db.execute(text('SELECT current_database(),current_user')).one())==('mindaam_staging','mindaam_staging')
 assert db.execute(text('SHOW transaction_read_only')).scalar()=='on'
 owners=list(db.execute(text("SELECT email,username,password_hash,must_change_password,verified,suspended FROM users WHERE role='super_admin'")).mappings())
 result={'read_only':True,'owner_count':len(owners),'credentials_changed':False,'roles_changed':False}
 if len(owners)==1:
  owner=owners[0]
  result.update({'email':owner['email'],'username':owner['username'],'must_change_password':owner['must_change_password'],'verified':owner['verified'],'suspended':owner['suspended'],'configured_email_matches':owner['email'].lower()==os.environ.get('SUPER_ADMIN_EMAIL','').lower(),'configured_username_matches':owner['username']==os.environ.get('SUPER_ADMIN_USERNAME',''),'initial_credential_matches':bool(os.environ.get('SUPER_ADMIN_INITIAL_PASSWORD')) and check_password(os.environ['SUPER_ADMIN_INITIAL_PASSWORD'],owner['password_hash'])})
 db_clock=float(db.execute(text('SELECT extract(epoch from clock_timestamp())')).scalar())
 import time
 result['database_epoch']=db_clock
 result['job_epoch']=time.time()
 result['reset_tokens']=[]
 result['identity_audit']=[]
 if len(owners)==1 and owners[0]['username']=='mindaam_owner' and owners[0]['email']=='sain@scalivora.com':
  result['reset_tokens']=[dict(row) for row in db.execute(text("SELECT created_at,expires_at,consumed_at FROM identity_tokens WHERE purpose='reset' AND user_id IN (SELECT id FROM users WHERE role='super_admin' AND username='mindaam_owner' AND email='sain@scalivora.com') ORDER BY created_at DESC LIMIT 10")).mappings()]
  result['identity_audit']=[dict(row) for row in db.execute(text("SELECT action,created_at FROM audit_logs WHERE target IN (SELECT id FROM users WHERE role='super_admin' AND username='mindaam_owner' AND email='sain@scalivora.com') AND action IN ('owner.recovery_issued','identity.password_reset','identity.email_queued') ORDER BY created_at DESC LIMIT 20")).mappings()]
 print('MINDAAM_OWNER_RECOVERY_REVIEW '+json.dumps(result,sort_keys=True))
'''

def run(c,sha):
 if c.project!='mindaam':raise Blocked('Owner review restricted to Mindaam staging')
 release=c.get_json(f'releases/{sha}/staging.json')
 if not release or release.get('sha')!=sha:raise Blocked('Exact staging release required')
 service=ready_service(c,'mindaam-staging');image=service['spec']['template']['spec']['containers'][0]['image']
 if release['image']!=image or release['revision']!=service['status']['latestReadyRevisionName']:raise Blocked('Staging owner review release drift')
 name='mindaam-migrate-staging';job=c.gc('run','jobs','describe',name,'--region='+c.region);c.owned(job.get('metadata',{}),name)
 spec=job['spec']['template']['spec']['template']['spec']
 if spec['containers'][0]['image']!=image or spec.get('serviceAccountName')!=c.sa('migrate'):raise Blocked('Existing owner review job identity drift')
 encoded=base64.b64encode(PROBE.encode()).decode()
 execution=c.gc('run','jobs','execute',name,'--region='+c.region,"--args=^|^-c|import base64;exec(base64.b64decode('"+encoded+"'))",'--wait')['metadata']['name']
 query='resource.type="cloud_run_job" AND labels."run.googleapis.com/execution_name"="'+execution+'" AND textPayload:"MINDAAM_OWNER_RECOVERY_REVIEW "'
 rows=[]
 for _ in range(12):
  rows=c.gc('logging','read',query,'--limit=5')
  if rows:break
  time.sleep(5)
 if len(rows)!=1:raise Blocked('Unique owner recovery review evidence unavailable')
 result=json.loads(rows[0]['textPayload'].split('MINDAAM_OWNER_RECOVERY_REVIEW ',1)[1])
 if result.get('read_only') is not True or result.get('credentials_changed') is not False or result.get('roles_changed') is not False:raise Blocked('Invalid read-only owner review')
 result.update({'sha':sha,'revision':release['revision'],'execution':execution,'observed_at':int(time.time())})
 Path('gcp-evidence').mkdir(exist_ok=True)
 Path('gcp-evidence/owner-recovery-review.json').write_text(json.dumps(result,indent=2))
 c.put_json(f'releases/{sha}/owner-recovery-review.json',result)
 print('Existing owner recovery facts recorded privately. No account, credential or role changed.')
