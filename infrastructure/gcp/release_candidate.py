"""Exact-image preparation authorization; never grants production approval."""
import json,re,time
from common import Blocked,HERE
from release_policy import evidence_name,profile,required_checks
from deploy import image_check
from readiness import ready_service

def selected(c,sha):
 if c.project!='mindaam' or not re.fullmatch(r'[a-f0-9]{40}',sha):raise Blocked('Invalid release candidate')
 intent=json.loads((HERE/'release-preparation.json').read_text())
 if intent.get('sha')!=sha or intent.get('preparation_authorized') is not True:raise Blocked('Exact-image preparation authorization required')
 release=c.get_json(f'releases/{sha}/{evidence_name()}')
 if not release or release.get('sha')!=sha or release.get('image')!=intent.get('image') or release.get('profile')!=profile():raise Blocked('Verified release image mismatch')
 image_check(c,release['image'])
 if not all(release.get('checks',{}).get(k) is True for k in required_checks(profile())):raise Blocked('Incomplete staging acceptance')
 service=ready_service(c,'mindaam-staging')
 if service['status']['latestReadyRevisionName']!=release['revision'] or service['spec']['template']['spec']['containers'][0]['image']!=release['image']:raise Blocked('Current staging image drift')
 return release

def fresh(evidence,sha,image):
 return isinstance(evidence,dict) and evidence.get('sha')==sha and evidence.get('image')==image and evidence.get('status')=='PASS' and evidence.get('cleanup') is True and 0<=time.time()-evidence.get('completed_at',0)<86400
