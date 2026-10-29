"""One-release, time-limited resume of measured resources; never substitutes browser PASS."""
import datetime,hashlib,json,os,subprocess,tempfile,zipfile
from pathlib import Path
from common import Cloud,Blocked,command
from evidence import verify

SHA='da2a01b72ba4052dd42e2527466164dadd3c5c5b'
RUN=40793486481
HEAD='bde7bab7a2d3e7c4ebb84c1695f185bd6b3d460c'
ARTIFACT=12862304724
DIGEST='c5825528e901df739fa29c219bd19297000b2c5319ded23412849f04cf4f871f'
REPO='scalivoraai-hash/Mindaam'


def validate_proof(run, artifact, release):
    if os.environ.get('RELEASE_SHA')!=SHA or release.get('sha')!=SHA:
        raise Blocked('Resource resume is limited to the recorded beta application release')
    if release.get('profile')!='limited-public-beta-v1' or release.get('revision')!='mindaam-staging-00009-f8l':
        raise Blocked('Recorded beta revision/profile mismatch')
    if (run.get('id')!=RUN or run.get('head_sha')!=HEAD or run.get('head_branch')!='main'
        or run.get('repository',{}).get('full_name')!=REPO or run.get('path')!='.github/workflows/gcp-deploy.yml'
        or run.get('event')!='workflow_dispatch' or run.get('status')!='completed'):
        raise Blocked('Unexpected browser evidence workflow provenance')
    created=datetime.datetime.fromisoformat(run['created_at'].replace('Z','+00:00'))
    age=datetime.datetime.now(datetime.timezone.utc)-created
    if not datetime.timedelta(0)<=age<=datetime.timedelta(days=7):
        raise Blocked('Recorded browser evidence expired; run fresh browser acceptance')
    if (artifact.get('id')!=ARTIFACT or artifact.get('workflow_run',{}).get('id')!=RUN
        or artifact.get('expired') or artifact.get('digest')!='sha256:'+DIGEST):
        raise Blocked('Unexpected browser artifact provenance/digest')


def main():
    c=Cloud(os.environ['MINDAAM_PROJECT_ID']);c.require_project()
    release=json.loads(Path('deployment-result.json').read_text())
    run=json.loads(command(['gh','api',f'repos/{REPO}/actions/runs/{RUN}']))
    artifact=json.loads(command(['gh','api',f'repos/{REPO}/actions/artifacts/{ARTIFACT}']))
    validate_proof(run,artifact,release)
    changed=command(['git','diff','--name-only',HEAD,'HEAD']).splitlines()
    if any(p.startswith('infrastructure/gcp/browser') or p in {'infrastructure/gcp/acceptance-checks.json','infrastructure/gcp/beta-policy.json'} for p in changed):
        raise Blocked('Browser contracts changed since recorded acceptance')
    with tempfile.TemporaryDirectory() as directory:
        archive=Path(directory)/'evidence.zip'
        with archive.open('wb') as output:
            subprocess.run(['gh','api',f'repos/{REPO}/actions/artifacts/{ARTIFACT}/zip'],stdout=output,check=True)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=DIGEST:
            raise Blocked('Browser artifact bytes do not match the recorded digest')
        with zipfile.ZipFile(archive) as source:
            recorded=json.loads(source.read('deployment-result.json'))
            if recorded!=release:raise Blocked('Browser evidence belongs to a different deployed image/revision')
            Path('gcp-evidence').mkdir(exist_ok=True)
            for name in ('direct.json','relay.json','browser.json'):
                Path('gcp-evidence',name).write_bytes(source.read('gcp-evidence/'+name))
    Path('gcp-evidence/browser-provenance.json').write_text(json.dumps({'run_id':RUN,'artifact_id':ARTIFACT,'archive_sha256':DIGEST,'sha':SHA,'reused_without_modification':True},indent=2))
    verify(c,SHA)

if __name__=='__main__':main()
