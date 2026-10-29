"""Read-only production credential, database and IAM verification using the release image."""
import json,os,tempfile,time
from pathlib import Path
from common import Blocked
from render import environment
from release_policy import evidence_name
from recovery import SHA,target

PROBE='''import os,json,psycopg
from psycopg.conninfo import conninfo_to_dict
result={'secret_injection':all(bool(os.environ.get(k)) for k in ('DATABASE_URL','REDIS_URL','LIVEKIT_API_KEY','LIVEKIT_API_SECRET','PULSEPOINT_SECRET','MAIL_ENCRYPTION_KEY','SUPER_ADMIN_EMAIL','SUPER_ADMIN_USERNAME','SUPER_ADMIN_INITIAL_PASSWORD'))}
try:
 p=conninfo_to_dict(os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://'));p['connect_timeout']=15
 with psycopg.connect(**p) as c:
  c.execute('SET TRANSACTION READ ONLY')
  identity=c.execute('SELECT current_database(),current_user').fetchone()
  result['database_identity']=identity==('mindaam_production','mindaam_production')
  rights=c.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
  result['restricted_role']=not any(rights)
  result['staging_denied']=not c.execute("SELECT has_database_privilege(current_user,'mindaam_staging','CONNECT')").fetchone()[0]
  result['schema_revision']=c.execute('SELECT version_num FROM alembic_version').fetchone()[0]
  result['postgis']=bool(c.execute('SELECT PostGIS_Version()').fetchone()[0])
  row=c.execute("SELECT email,username,password_hash,must_change_password,verified,suspended FROM users WHERE role='super_admin'").fetchall()
  from backend.api.auth import check_password
  result['owner_count']=len(row)
  result['owner_credential_verified']=bool(len(row)==1 and row[0][0].lower()==os.environ['SUPER_ADMIN_EMAIL'].lower() and row[0][1]==os.environ['SUPER_ADMIN_USERNAME'] and row[0][4] and not row[0][5] and check_password(os.environ['SUPER_ADMIN_INITIAL_PASSWORD'],row[0][2]))
  result['owner_initial_change_required']=bool(len(row)==1 and row[0][3])
except Exception as e:
 result['runtime_failure_type']=type(e).__name__
print('MINDAAM_SECURITY_RESULT '+json.dumps(result))
'''


def run(c,sha):
 if sha!=SHA or c.project!='mindaam':raise Blocked('Security review limited to approved release')
 release=c.get_json(f'releases/{sha}/{evidence_name()}')
 if not release:raise Blocked('Verified staging evidence required')
 recovery=c.get_json(f'releases/{sha}/recovery.json')
 if not recovery or recovery.get('status')!='PASS' or recovery.get('cleanup') is not True:raise Blocked('Actual restore and cleanup must pass first')
 run_id=os.environ['GITHUB_RUN_ID'];name=target(run_id,os.environ['GITHUB_RUN_ATTEMPT']).replace('recovery','security')
 policy=c.gc('projects','get-iam-policy',c.project)
 roles=[b['role'] for b in policy.get('bindings',[]) if 'serviceAccount:'+c.sa('production') in b.get('members',[])]
 if set(roles)-{'roles/cloudsql.client','roles/logging.logWriter','roles/monitoring.metricWriter'}:raise Blocked('Unexpected project-wide production runtime permission')
 ordinary,secrets=environment(c,'production','https://mindaam.com')
 spec={'serviceAccountName':c.sa('production'),'timeoutSeconds':'120','maxRetries':0,'containers':[{'image':release['image'],'command':['python'],'args':['-c',PROBE], 'resources':{'limits':{'cpu':'1','memory':'512Mi'}},'env':[{'name':k,'value':v} for k,v in ordinary.items()]+[{'name':k,'valueFrom':{'secretKeyRef':{'name':v,'key':'latest'}}} for k,v in secrets.items()]}]}
 manifest={'apiVersion':'run.googleapis.com/v1','kind':'Job','metadata':{'name':name,'labels':{'application':'mindaam','security_run':run_id}},'spec':{'template':{'spec':{'taskCount':1,'parallelism':1,'template':{'metadata':{'annotations':{'run.googleapis.com/cloudsql-instances':f'{c.project}:{c.region}:mindaam-postgres'}},'spec':spec}}}}}
 evidence={'sha':sha,'image':release['image'],'run_id':run_id,'runtime_roles':roles,'status':'FAIL','checks':{},'cleanup':False}
 created=False
 try:
  with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
   json.dump(manifest,f);f.flush();c.gc('run','jobs','replace',f.name,'--region='+c.region)
  created=True
  execution=c.gc('run','jobs','execute',name,'--region='+c.region,'--wait')['metadata']['name']
  query='resource.type="cloud_run_job" AND labels."run.googleapis.com/execution_name"="'+execution+'" AND textPayload:"MINDAAM_SECURITY_RESULT "'
  rows=[]
  for _ in range(12):
   rows=c.gc('logging','read',query,'--limit=5')
   if rows:break
   time.sleep(5)
  if len(rows)!=1:raise Blocked('Unique security runtime evidence unavailable')
  evidence['checks']=json.loads(rows[0]['textPayload'].split('MINDAAM_SECURITY_RESULT ',1)[1])
  keys=('secret_injection','database_identity','restricted_role','staging_denied','postgis','owner_credential_verified')
  evidence['status']='PASS' if all(evidence['checks'].get(k) is True for k in keys) else 'FAIL'
 finally:
  if created:c.gc('run','jobs','delete',name,'--region='+c.region);evidence['cleanup']=True
  evidence['completed_at']=int(time.time())
  Path('gcp-evidence').mkdir(exist_ok=True)
  Path('gcp-evidence/security-runtime.json').write_text(json.dumps(evidence,indent=2))
  c.put_json(f'releases/{sha}/security-runtime.json',evidence)
 if evidence['status']!='PASS':raise Blocked('Production runtime security checks failed; inspect non-secret evidence')
