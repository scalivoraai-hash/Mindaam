"""Read-only aggregate PC audit using the existing production migration job."""
import base64,json,time,subprocess
from pathlib import Path
from common import Blocked
from readiness import ready_service

def probe_source():
 path=Path(__file__).resolve().parents[2]/'backend/api/ledger_reconciliation.py'
 # The already CI-validated candidate supplies the read-only reviewer before merge.
 source=(path.read_text() if path.exists() else subprocess.run(['git','show','99fdcf7f20ca171592782c7e68bfdd0a28b6a4cc:backend/api/ledger_reconciliation.py'],check=True,capture_output=True,text=True,cwd=Path(__file__).resolve().parents[2]).stdout).split("if __name__=='__main__':")[0].replace('from .models import Ledger','from backend.api.models import Ledger')
 return '''import os,json
os.environ['DATABASE_URL']=os.environ['RUNTIME_DATABASE_URL']
from backend.api.db import SessionLocal
from sqlalchemy import text
'''+source+'''
with SessionLocal.begin() as db:
 db.execute(text('SET TRANSACTION READ ONLY'))
 identity=tuple(db.execute(text('SELECT current_database(),current_user')).one())
 assert identity==('mindaam_production','mindaam_production')
 assert db.execute(text('SHOW transaction_read_only')).scalar()=='on'
 result=inspect(db);result.pop('accounts')
 result['database_identity_verified']=True
 print('MINDAAM_LEDGER_DRY_RUN '+json.dumps(result,sort_keys=True))
'''

def run(c,sha):
 if c.project!='mindaam':raise Blocked('Ledger review restricted to Mindaam')
 release=c.get_json(f'releases/{sha}/production.json')
 if not release or release.get('sha')!=sha:raise Blocked('Existing exact production release required')
 current=ready_service(c,'mindaam-production')
 image=current['spec']['template']['spec']['containers'][0]['image']
 if release['image']!=image or release['revision']!=current['status']['latestReadyRevisionName']:raise Blocked('Production release drift')
 name='mindaam-migrate-production'
 job=c.gc('run','jobs','describe',name,'--region='+c.region)
 c.owned(job.get('metadata',{}),name)
 spec=job['spec']['template']['spec']['template']['spec']
 if spec['containers'][0]['image']!=image or spec.get('serviceAccountName')!=c.sa('migrate'):raise Blocked('Existing audit execution image or identity drift')
 encoded=base64.b64encode(probe_source().encode()).decode()
 # Override this execution only. Never run migrations or update the job definition.
 args="--args=^|^-c|import base64;exec(base64.b64decode('"+encoded+"'))"
 execution=c.gc('run','jobs','execute',name,'--region='+c.region,args,'--wait')['metadata']['name']
 query='resource.type="cloud_run_job" AND labels."run.googleapis.com/execution_name"="'+execution+'" AND textPayload:"MINDAAM_LEDGER_DRY_RUN "'
 rows=[]
 for _ in range(12):
  rows=c.gc('logging','read',query,'--limit=5')
  if rows:break
  time.sleep(5)
 if len(rows)!=1:raise Blocked('Unique read-only ledger evidence unavailable')
 result=json.loads(rows[0]['textPayload'].split('MINDAAM_LEDGER_DRY_RUN ',1)[1])
 if result.get('adjustments_applied') is not False or result.get('mode')!='DRY_RUN_ONLY' or 'accounts' in result or result.get('database_identity_verified') is not True:raise Blocked('Invalid aggregate-only ledger evidence')
 result.update({'sha':sha,'image':image,'revision':release['revision'],'execution':execution,'observed_at':int(time.time())})
 Path('gcp-evidence').mkdir(exist_ok=True)
 Path('gcp-evidence/ledger-review.json').write_text(json.dumps(result,indent=2))
 c.put_json(f'releases/{sha}/ledger-review.json',result)
 print('Actual aggregate ledger dry run recorded. No balances changed; owner review and backup required before adjustments.')
