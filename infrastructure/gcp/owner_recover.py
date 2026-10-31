"""Owner-run staging recovery. No public endpoint, IAM grant or password reset bypass."""
import argparse
import base64
import json
import os
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from common import Blocked, Cloud, command
from readiness import ready_service

OWNER = 'sain@scalivora.com'
ORIGIN = 'https://mindaam-staging-qfrofqn4pq-nw.a.run.app'

# Executed by the existing restricted staging job, only after the Cloud Shell
# caller's Google identity and existing project permissions have been verified.
ISSUE = '''
def issue(db, principal):
 from sqlalchemy import select
 from backend.api.models import User, Audit
 from backend.api.identity import IdentityToken
 import hashlib,secrets,time,os
 if principal != 'sain@scalivora.com':raise ValueError('Owner identity mismatch')
 owners=list(db.scalars(select(User).where(User.role=='super_admin').with_for_update()))
 if len(owners)!=1:raise ValueError('Exactly one existing owner required')
 owner=owners[0]
 if owner.email!=principal or owner.username!='mindaam_owner' or owner.suspended or not owner.verified:
  raise ValueError('Existing verified owner mismatch')
 now=time.time()
 tokens=list(db.scalars(select(IdentityToken).where(IdentityToken.user_id==owner.id,IdentityToken.purpose=='reset')))
 if any(t.created_at>now-60 for t in tokens):raise ValueError('Recovery already requested recently')
 for token in tokens:
  if token.consumed_at is None:token.consumed_at=now
 raw=secrets.token_urlsafe(40)
 db.add(IdentityToken(id=hashlib.sha256(raw.encode()).hexdigest(),user_id=owner.id,purpose='reset',expires_at=now+600))
 db.add(Audit(actor_id=owner.id,action='owner.recovery_issued',target=owner.id,details={'channel':'owner_google_cloud_shell','principal':principal,'execution':os.getenv('CLOUD_RUN_EXECUTION'),'expires_in_seconds':600}))
 db.flush()
 return raw
'''

def verified_owner(info):
    if info.get('email') != OWNER or info.get('verified_email') is not True:
        raise Blocked('Authenticate Google Cloud as the existing verified owner: '+OWNER)

class OwnerCloud(Cloud):
    def gc(self, *args, **kwargs):
        kwargs['sensitive'] = True
        return super().gc(*args, '--account='+OWNER, **kwargs)

    def get_json(self, key):
        return json.loads(command(['gcloud','storage','cat',f'gs://{self.bucket}/{key}',
                                   '--project='+self.project,'--account='+OWNER], sensitive=True))

def run(sha, destination):
    if os.getenv('CI') or os.getenv('GITHUB_ACTIONS'):
        raise Blocked('Run privately in the owner Cloud Shell, never in CI')
    if not re.fullmatch('[a-f0-9]{40}',sha):raise Blocked('Exact staging SHA required')
    # Use Google's authenticated response, not an unverified email argument/JWT.
    access=command(['gcloud','auth','print-access-token','--account='+OWNER],sensitive=True)
    try:
        request=Request('https://www.googleapis.com/oauth2/v2/userinfo',headers={'Authorization':'Bearer '+access})
        with urlopen(request,timeout=20) as response:verified_owner(json.load(response))
    finally:
        del access
    c=OwnerCloud('mindaam');c.require_project()
    release=c.get_json(f'releases/{sha}/staging.json')
    service=ready_service(c,'mindaam-staging')
    image=service['spec']['template']['spec']['containers'][0]['image']
    if release.get('sha')!=sha or release.get('image')!=image or release.get('revision')!=service['status']['latestReadyRevisionName'] or release.get('origin')!=ORIGIN:
        raise Blocked('Exact staging release drift')
    job=c.gc('run','jobs','describe','mindaam-migrate-staging','--region='+c.region)
    c.owned(job.get('metadata',{}),'mindaam-migrate-staging')
    spec=job['spec']['template']['spec']['template']['spec']
    if spec['containers'][0]['image']!=image or spec.get('serviceAccountName')!=c.sa('migrate'):
        raise Blocked('Existing recovery job identity drift')
    from cryptography.hazmat.primitives.asymmetric import rsa,padding
    from cryptography.hazmat.primitives import hashes,serialization
    private=rsa.generate_private_key(public_exponent=65537,key_size=3072)
    public=base64.b64encode(private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
    probe="""import os,base64
os.environ['DATABASE_URL']=os.environ['RUNTIME_DATABASE_URL']
from backend.api.db import SessionLocal
from sqlalchemy import text
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding
"""+ISSUE+f"""
assert os.environ.get('APP_ENV')=='staging'
with SessionLocal.begin() as db:
 assert tuple(db.execute(text('SELECT current_database(),current_user')).one())==('mindaam_staging','mindaam_staging')
 raw=issue(db,{OWNER!r})
 key=serialization.load_pem_public_key(base64.b64decode({public!r}))
 ciphertext=key.encrypt(raw.encode(),padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
print('MINDAAM_OWNER_RECOVERY_CIPHERTEXT '+base64.b64encode(ciphertext).decode())
"""
    # Reserve a private, new file before issuing a token. Refuse symlinks/overwrite.
    fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        encoded=base64.b64encode(probe.encode()).decode()
        execution=c.gc('run','jobs','execute','mindaam-migrate-staging','--region='+c.region,
                       "--args=^|^-c|import base64;exec(base64.b64decode('"+encoded+"'))",'--wait')['metadata']['name']
        query='resource.type="cloud_run_job" AND labels."run.googleapis.com/execution_name"="'+execution+'" AND textPayload:"MINDAAM_OWNER_RECOVERY_CIPHERTEXT "'
        rows=[]
        for _ in range(12):
            rows=c.gc('logging','read',query,'--limit=2')
            if rows:break
            time.sleep(5)
        if len(rows)!=1:raise Blocked('Recovery output unavailable; do not repeat immediately')
        encrypted=base64.b64decode(rows[0]['textPayload'].split('MINDAAM_OWNER_RECOVERY_CIPHERTEXT ',1)[1])
        raw=private.decrypt(encrypted,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None)).decode()
        with os.fdopen(fd,'w') as output:
            fd=None;output.write(ORIGIN+'/reset-password#token='+raw+'\n')
        print('One-use recovery link saved privately to '+str(destination)+'. Open it within 10 minutes, set your password, then delete this file. No password or role has been changed by this operation.')
    finally:
        if fd is not None:os.close(fd);Path(destination).unlink(missing_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-sha',required=True)
    parser.add_argument('--confirm-owner-recovery',action='store_true',required=True)
    args=parser.parse_args()
    try:run(args.release_sha,Path.home()/'mindaam-staging-owner-reset.txt')
    except Exception:
        # Provider exceptions can contain credential-bearing request details.
        raise SystemExit('Recovery stopped. No secret printed. Check owner authentication, exact staging SHA and GCP audit logs.') from None
