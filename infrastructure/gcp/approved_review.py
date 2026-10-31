"""Validate exact-image evidence; publish only an authenticated owner's explicit approval."""
import time
from common import Blocked
from review import save,inventory
from release_candidate import selected,fresh
from readiness import ready_service
OWNER='sain@scalivora.com'

def prepare(c,sha):
 release=selected(c,sha);prefix=f'releases/{sha}/'
 review=c.get_json(prefix+'review-draft.json')
 if not review or review.get('sha')!=sha or review.get('image')!=release['image']:raise Blocked('Exact-image cost draft required')
 runtime=c.get_json(prefix+'security-runtime.json');recovery=c.get_json(prefix+'recovery.json')
 if not all(fresh(e,sha,release['image']) for e in (runtime,recovery)):raise Blocked('Fresh exact-image security, restore and cleanup required')
 required=('secret_injection','database_identity','restricted_role','staging_denied','staging_role_denied_production','postgis','owner_identity_verified','unauthenticated_admin_denied','wrong_password_denied','payments_gated')
 if not all(runtime.get('checks',{}).get(k) is True for k in required):raise Blocked('Incomplete runtime security evidence')
 access=c.get_json(prefix+'owner-access.json')
 if not access or access.get('sha')!=sha or access.get('image')!=release['image'] or access.get('principal')!=OWNER or access.get('status')!='PASS' or not 0<=time.time()-access.get('completed_at',0)<86400:raise Blocked('Fresh authenticated owner access required for both environments')
 for env in ('staging','production'):
  checks=access.get('environments',{}).get(env,{})
  if checks.get('owner_identity')!=OWNER or not all(checks.get(k) is True for k in ('owner_login','dashboard','secure_cookie','logout')):raise Blocked('Incomplete '+env+' owner access evidence')
  service=ready_service(c,'mindaam-'+env)
  if checks.get('revision')!=service['status']['latestReadyRevisionName'] or checks.get('image')!=service['spec']['template']['spec']['containers'][0]['image']:raise Blocked('Owner access revision drift')
 for scenario,approved in [('idle',48.76),('light',91.98)]:
  if abs(sum(review['costs'][scenario]['usd'].values())-approved)>.01:raise Blocked('Cost model changed; renewed review required')
 current=inventory(c)
 if current['sql']['settings']['tier']!=review['inventory']['sql']['settings']['tier'] or current['vm']['machineType']!=review['inventory']['vm']['machineType'] or current['production_limits']!=review['inventory']['production_limits']:raise Blocked('Infrastructure configuration drift')
 security={'sha':sha,'image':release['image'],'evidence_object':f'gs://{c.bucket}/{prefix}security-review.json','owner_access_verified':True,'production_secrets_verified':True,'database_isolation_verified':True,'backup_restore_verified':True,'public_launch_safeguards_verified':True,'owner_access_scope':'Independent existing staging and production HTTPS owner login, dashboard, cookie and logout checks; exact-image runtime security tested separately.','runtime_evidence':f'gs://{c.bucket}/{prefix}security-runtime.json','recovery_evidence':f'gs://{c.bucket}/{prefix}recovery.json','owner_access_evidence':f'gs://{c.bucket}/{prefix}owner-access.json','reviewed_at':int(time.time())}
 review.update(security_review=security,owner_approved=False,readiness='AWAITING EXACT-IMAGE OWNER APPROVAL')
 return review

def finalise(c,sha):
 review=prepare(c,sha)
 approval=c.get_json(f'releases/{sha}/owner-release-approval.json')
 if not approval or approval.get('sha')!=sha or approval.get('image')!=review['image'] or approval.get('principal')!=OWNER or approval.get('owner_approved') is not True or not 0<=time.time()-approval.get('approved_at',0)<86400:raise Blocked('Fresh authenticated exact-image owner approval required')
 # Finalisation cannot be invoked by CI or by an unverified service-account adapter.
 if getattr(c,'verified_owner_principal',None)!=OWNER:raise Blocked('Finalise privately as the authenticated owner')
 c.put_json(f'releases/{sha}/security-review.json',review['security_review'])
 review.update(owner_approved=True,cost_approval_status='STANDING COST POLICY; EXACT-IMAGE OWNER APPROVAL RECORDED',readiness='MANDATORY PREDEPLOYMENT CHECKS PASSED',owner_approval=approval)
 save(c,sha,review)
