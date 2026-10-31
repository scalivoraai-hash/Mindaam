"""Exact-release recovery drill; never restores into an existing instance."""
import json
import os
import re
import tempfile
import time
from pathlib import Path
from common import Blocked, command
from render import postgres
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from release_policy import evidence_name
# Existing production approval remains pinned separately from a recovery drill.
SHA = '1af2051d13e56aff76ec69ad0cbcec73146aa7df'


def target(run, attempt):
    if not re.fullmatch(r'[0-9]{1,15}', run) or not re.fullmatch(r'[0-9]{1,3}', attempt):
        raise Blocked('Valid GitHub run and attempt required')
    return f'mindaam-recovery-{run}-{attempt}'


def guard(resource, name, run):
    if not name.startswith('mindaam-recovery-') or resource.get('name') != name:
        raise Blocked('Recovery target mismatch')
    labels = resource.get('settings', {}).get('userLabels', resource.get('metadata', {}).get('labels', {}))
    if labels.get('application') != 'mindaam' or labels.get('recovery_run') != run:
        raise Blocked('Recovery ownership mismatch')


PROBE = '''import os,json,psycopg
from psycopg.conninfo import conninfo_to_dict
p=conninfo_to_dict(os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://'))
p['host']='/cloudsql/'+os.environ['RECOVERY_CONNECTION']
p['connect_timeout']=20
result={}
for name in ('mindaam_staging','mindaam_production'):
 p['dbname']=name
 with psycopg.connect(**p) as c:
  c.execute('SET TRANSACTION READ ONLY')
  tables=c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'").fetchall()
  names={r[0] for r in tables}
  item={'connected':True,'tables':len(names)}
  if name=='mindaam_staging':
   assert {'users','events','alembic_version','wallet_transactions'} <= names
   item['postgis']=c.execute('SELECT PostGIS_Version()').fetchone()[0]
   item['schema_revision']=c.execute('SELECT version_num FROM alembic_version').fetchone()[0]
   item['user_count']=c.execute('SELECT count(*) FROM users').fetchone()[0]
   assert item['user_count']>0
   item['event_count']=c.execute('SELECT count(*) FROM events').fetchone()[0]
  elif 'alembic_version' in names:
   item['schema_revision']=c.execute('SELECT version_num FROM alembic_version').fetchone()[0]
  else:
   assert not names, 'Unexpected partial production schema'
   item['state']='empty_before_first_production_migration'
  result[name]=item
print('MINDAAM_RECOVERY_RESULT '+json.dumps(result))
'''


def run(c, sha):
    from release_candidate import selected
    release=selected(c,sha)
    run_id=os.environ['GITHUB_RUN_ID']; name=target(run_id,os.environ['GITHUB_RUN_ATTEMPT'])
    source=c.gc('sql','instances','describe','mindaam-postgres'); c.owned(source,'source')
    settings=source['settings']
    if settings['tier']!='db-f1-micro' or int(settings['dataDiskSizeGb'])>20 or source['databaseVersion']!='POSTGRES_16':
        raise Blocked('Recovery size exceeds reviewed configuration')
    instances=c.gc('sql','instances','list')
    if any(x['name'].startswith('mindaam-recovery-') for x in instances):
        raise Blocked('Existing recovery instance requires cleanup before another drill')
    backups=c.gc('sql','backups','list','--instance=mindaam-postgres','--limit=20')
    successful=[x for x in backups if x.get('status')=='SUCCESSFUL']
    if not successful: raise Blocked('No successful backup')
    backup=max(successful,key=lambda x:x['endTime'])
    evidence={'sha':sha,'image':release['image'],'run_id':run_id,'backup_id':backup['id'],
              'source':'mindaam-postgres','target':name,'status':'RUNNING','checks':{},'cleanup':False}
    Path('gcp-evidence').mkdir(exist_ok=True)
    created=False; job_created=False
    try:
        payload=postgres(c);payload['name']=name
        payload['settings'].pop('storageAutoResizeLimit',None)
        payload['settings'].update({'deletionProtectionEnabled':False,'storageAutoResize':False,
            'dataDiskSizeGb':settings['dataDiskSizeGb'], 'backupConfiguration':{'enabled':False},
            'userLabels':{'application':'mindaam','recovery_run':run_id}})
        token=command(['gcloud','auth','print-access-token'],sensitive=True)
        request=Request(f'https://sqladmin.googleapis.com/sql/v1beta4/projects/{c.project}/instances',
            data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        try:
            with urlopen(request,timeout=60) as response: operation=json.load(response)
        except HTTPError as error:
            detail=json.loads(error.read()).get('error',{}).get('message','No provider detail')
            raise Blocked('Recovery create HTTP '+str(error.code)+': '+detail[:1000]) from None
        created=True
        print('Temporary recovery instance creation accepted: '+name,flush=True)
        c.gc('sql','operations','wait',operation['name'],'--timeout=1800')
        guard(c.gc('sql','instances','describe',name),name,run_id)
        operation=c.gc('sql','backups','restore',str(backup['id']),'--backup-instance=mindaam-postgres','--restore-instance='+name,'--async')
        evidence['restore_operation']=operation['name']
        print('Waiting for actual Cloud SQL restore operation '+operation['name'],flush=True)
        c.gc('sql','operations','wait',operation['name'],'--timeout=3600')
        connection=f'{c.project}:{c.region}:{name}'
        manifest={'apiVersion':'run.googleapis.com/v1','kind':'Job','metadata':{'name':name,'labels':{'application':'mindaam','recovery_run':run_id}},
          'spec':{'template':{'spec':{'taskCount':1,'parallelism':1,'template':{'metadata':{'annotations':{'run.googleapis.com/cloudsql-instances':connection}},'spec':{
           'serviceAccountName':c.sa('migrate'),'timeoutSeconds':'300','maxRetries':0,'containers':[{'image':release['image'],'command':['python'],'args':['-c',PROBE],
           'resources':{'limits':{'cpu':'1','memory':'512Mi'}},'env':[{'name':'RECOVERY_CONNECTION','value':connection},
           {'name':'DATABASE_URL','valueFrom':{'secretKeyRef':{'name':'mindaam-staging-migration-url','key':'latest'}}}]}]}}}}}}
        manifest['spec']['template']['metadata']=manifest['spec']['template']['spec']['template'].pop('metadata')
        with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
            json.dump(manifest,f);f.flush();c.gc('run','jobs','replace',f.name,'--region='+c.region)
        job_created=True
        execution=c.gc('run','jobs','execute',name,'--region='+c.region,'--wait')['metadata']['name']
        query='resource.type="cloud_run_job" AND labels."run.googleapis.com/execution_name"="'+execution+'" AND textPayload:"MINDAAM_RECOVERY_RESULT "'
        rows=[]
        for _ in range(12):
            rows=c.gc('logging','read',query,'--limit=5')
            if rows: break
            time.sleep(5)
        if len(rows)!=1: raise Blocked('Unique recovery result not available')
        evidence['checks']=json.loads(rows[0]['textPayload'].split('MINDAAM_RECOVERY_RESULT ',1)[1])
        evidence['status']='PASS'
    except Exception as error:
        evidence['status']='FAIL'
        evidence['failure']=str(error)[-1500:]
        raise
    finally:
        # Only resources created by this invocation can be removed.
        if job_created:
            c.gc('run','jobs','delete',name,'--region='+c.region)
        if created:
            for op in c.gc('sql','operations','list','--instance='+name,'--filter=status!=DONE'):
                c.gc('sql','operations','wait',op['name'],'--timeout=3600')
            guard(c.gc('sql','instances','describe',name),name,run_id)
            c.gc('sql','instances','delete',name)
            evidence['cleanup']=not any(x['name']==name for x in c.gc('sql','instances','list'))
        evidence['completed_at']=int(time.time())
        Path('gcp-evidence/recovery.json').write_text(json.dumps(evidence,indent=2))
        c.put_json(f'releases/{sha}/recovery.json',evidence)
    if not evidence['cleanup']: raise Blocked('Recovery cleanup not verified')
