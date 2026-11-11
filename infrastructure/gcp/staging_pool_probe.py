"""Bounded read-only pool diagnosis on the existing staging image and identity."""
import json, os, tempfile, time
from common import Blocked

QUERY = """SELECT coalesce(state,'unknown'), coalesce(wait_event_type,'none'),
 coalesce(wait_event,'none'), count(*),
 coalesce(max(extract(epoch from clock_timestamp()-xact_start)),0)::float8,
 coalesce(max(extract(epoch from clock_timestamp()-query_start)),0)::float8
 FROM pg_stat_activity
 WHERE datname=current_database() AND usename=current_user AND pid<>pg_backend_pid()
 GROUP BY state,wait_event_type,wait_event ORDER BY 1,2,3"""

PROBE = '''import os,json,time,psycopg
from psycopg.conninfo import conninfo_to_dict
p=conninfo_to_dict(os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://'))
p['connect_timeout']=5
p['options']='-c default_transaction_read_only=on -c statement_timeout=2000'
result={'read_only':True,'samples':[]}
started=time.monotonic()
connection=psycopg.connect(**p,autocommit=True)
result['connection_ms']=round(1000*(time.monotonic()-started),3)
with connection as c:
 assert c.execute('SELECT current_database(),current_user').fetchone()==('mindaam_staging','mindaam_staging')
 assert c.execute('SHOW default_transaction_read_only').fetchone()[0]=='on'
 result['settings']=dict(c.execute("SELECT name,setting FROM pg_settings WHERE name IN ('synchronous_commit','fsync','wal_sync_method','commit_delay','commit_siblings','track_io_timing','track_wal_io_timing')").fetchall())
 wal_query='SELECT wal_records::float8,wal_bytes::float8,wal_write::float8,wal_sync::float8,wal_write_time::float8,wal_sync_time::float8 FROM pg_stat_wal'
 result['wal_before']=list(c.execute(wal_query).fetchone())
 for i in range(60):
  started=time.monotonic()
  rows=c.execute(QUERY).fetchall()
  elapsed=round(1000*(time.monotonic()-started),3)
  result['samples'].append({'at':time.time(),'query_ms':elapsed,'groups':[dict(zip(('state','wait_type','wait','connections','oldest_transaction_seconds','oldest_query_seconds'),r)) for r in rows]})
  if i<59:time.sleep(.5)
 result['wal_after']=list(c.execute(wal_query).fetchone())
 result['wal_fields']=['records','bytes','writes','syncs','write_ms','sync_ms']
print('MINDAAM_POOL_RESULT '+json.dumps(result,separators=(',',':')))
'''


def collect(c, release):
    run=os.environ['GITHUB_RUN_ID']; attempt=os.environ['GITHUB_RUN_ATTEMPT']
    from recovery import target
    name=target(run,attempt).replace('recovery','pool-probe')
    if c.project!='mindaam' or release.get('environment')!='staging':
        raise Blocked('Pool probe is staging only')
    spec={'serviceAccountName':c.sa('staging'),'timeoutSeconds':'90','maxRetries':0,
          'containers':[{'image':release['image'],'command':['python'],
             'args':['-c','QUERY='+repr(QUERY)+'\n'+PROBE],
             'resources':{'limits':{'cpu':'1','memory':'512Mi'}},
             'env':[{'name':'DATABASE_URL','valueFrom':{'secretKeyRef':{'name':'mindaam-staging-database-url','key':'latest'}}}]}]}
    job={'apiVersion':'run.googleapis.com/v1','kind':'Job',
         'metadata':{'name':name,'labels':{'application':'mindaam','diagnostic_run':run}},
         'spec':{'template':{'metadata':{'annotations':{
            'run.googleapis.com/cloudsql-instances':f'{c.project}:{c.region}:mindaam-postgres',
            'run.googleapis.com/network-interfaces':'[{"network":"mindaam","subnetwork":"mindaam-run"}]',
            'run.googleapis.com/vpc-access-egress':'private-ranges-only'}},
            'spec':{'taskCount':1,'parallelism':1,'template':{'spec':spec}}}}}
    created=False
    try:
        with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
            json.dump(job,f);f.flush();c.gc('run','jobs','replace',f.name,'--region='+c.region)
        created=True
        execution=c.gc('run','jobs','execute',name,'--region='+c.region,'--wait')['metadata']['name']
        query='resource.type="cloud_run_job" AND labels."run.googleapis.com/execution_name"="'+execution+'" AND textPayload:"MINDAAM_POOL_RESULT "'
        rows=[]
        for _ in range(6):
            rows=c.gc('logging','read',query,'--limit=2')
            if rows:break
            time.sleep(2)
        if len(rows)!=1:raise Blocked('Unique staging pool result unavailable')
        result=json.loads(rows[0]['textPayload'].split('MINDAAM_POOL_RESULT ',1)[1])
        if result.get('read_only') is not True or len(result.get('samples',[]))!=60:
            raise Blocked('Incomplete staging pool sample')
        return result
    finally:
        if created:c.gc('run','jobs','delete',name,'--region='+c.region)
