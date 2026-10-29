"""Finalise the owner's approved cost model only from actual exact-release evidence."""
import time
from common import Blocked
from review import save,inventory
from recovery import SHA


def finalise(c,sha):
 if sha!=SHA:raise Blocked('Owner approval belongs to a different release')
 prefix=f'releases/{sha}/'
 review=c.get_json(prefix+'review-draft.json')
 approval=c.get_json(prefix+'owner-cost-approval.json')
 runtime=c.get_json(prefix+'security-runtime.json')
 recovery=c.get_json(prefix+'recovery.json')
 if not approval or approval.get('owner_approved') is not True:raise Blocked('Explicit owner cost approval missing')
 if not review or review.get('sha')!=sha:raise Blocked('Exact release cost draft missing')
 for evidence in (runtime,recovery):
  if not evidence or evidence.get('sha')!=sha or evidence.get('image')!=review['image'] or evidence.get('status')!='PASS' or evidence.get('cleanup') is not True or not 0<=time.time()-evidence.get('completed_at',0)<86400:
   raise Blocked('Fresh successful security, restore and cleanup evidence required')
 for scenario in ('idle','light'):
  if abs(sum(review['costs'][scenario]['usd'].values())-approval[scenario+'_usd'])>.01:raise Blocked('Cost model differs from owner approval')
 if sum(review['costs']['light']['usd'].values())>150:raise Blocked('Renewed owner cost approval required')
 checks=runtime['checks']
 required=('secret_injection','database_identity','restricted_role','staging_denied','staging_role_denied_production','postgis','owner_credential_verified','unauthenticated_admin_denied','wrong_password_denied','owner_login','secure_cookie','initial_change_enforced','logout','payments_gated')
 if not all(checks.get(k) is True for k in required):raise Blocked('Incomplete production runtime evidence')
 current=inventory(c)
 if current['sql']['settings']['tier']!=review['inventory']['sql']['settings']['tier'] or current['vm']['machineType']!=review['inventory']['vm']['machineType'] or current['production_limits']!=review['inventory']['production_limits']:raise Blocked('Infrastructure configuration differs from approved model')
 security={'sha':sha,'image':review['image'],'evidence_object':f'gs://{c.bucket}/{prefix}security-review.json',
 'owner_access_verified':True,'production_secrets_verified':True,'database_isolation_verified':True,
 'backup_restore_verified':True,'public_launch_safeguards_verified':True,
 'owner_access_scope':'Actual initial admin login with forced password change; dashboard remains denied until owner completes setup.',
 'runtime_evidence':f'gs://{c.bucket}/{prefix}security-runtime.json','recovery_evidence':f'gs://{c.bucket}/{prefix}recovery.json',
 'reviewed_at':int(time.time())}
 c.put_json(prefix+'security-review.json',security)
 review.update({'security_review':security,'owner_approved':True,'cost_approval_status':'APPROVED BY OWNER','readiness':'MANDATORY PREDEPLOYMENT CHECKS PASSED'})
 save(c,sha,review)
