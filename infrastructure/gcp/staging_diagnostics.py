"""Read-only, exact-revision failure evidence. Never exports log payloads or secrets."""
import datetime,json,re
from urllib.parse import urlsplit
from pathlib import Path
from common import Blocked,command
from readiness import ready_service
from diagnostics import get_json
from urllib.parse import urlencode

PATTERNS={
 'readiness_dependency':r'Readiness failed dependency=(?:database|postgis_catalogue|redis) exception=[A-Za-z][A-Za-z0-9_]*',
 'pool_exhaustion':r'QueuePool limit of size \d+ overflow \d+ reached, connection timed out, timeout [\d.]+',
 'statement_timeout':r'canceling statement due to statement timeout',
 'lock_timeout':r'canceling statement due to lock timeout',
 'deadlock':r'deadlock detected',
 'connection_limit':r'(?:too many clients already|remaining connection slots are reserved)',
 'connection_closed':r'(?:server closed the connection unexpectedly|SSL connection has been closed unexpectedly)',
 'out_of_memory':r'(?:out of memory|Memory limit of [\d.]+ [A-Za-z]+ exceeded)',
 'no_available_instance':r'no available instance',
 'connection_refused':r'Connection refused',
 'database_starting':r'database system is (?:starting up|shutting down|in recovery mode)',
 'connection_reset':r'(?:Connection reset by peer|SSL SYSCALL error: EOF detected|consuming input failed)',
 'connection_timeout':r'(?:connection timeout expired|timeout expired|could not receive data from server)',
 'worker_exit':r'(?:WORKER TIMEOUT|Worker failed to boot|SIGKILL|signal 9|signal 11)',
 'malformed_response':r'(?:malformed response|connection to the instance had an error|instance could not start successfully|container failed to start)',
 'auth_failed':r'password authentication failed',
 'dns_failure':r'could not translate host name',
 'exception_type':r'(?:sqlalchemy(?:\.orm)?\.exc|psycopg\.errors|psycopg)\.[A-Za-z]+Error',
}

def summarize(rows):
 result=[]
 for row in rows:
  text=row.get('textPayload','')+' '+str(row.get('jsonPayload',{}).get('message',''))
  matches={key:sorted(set(re.findall(pattern,text,re.I))) for key,pattern in PATTERNS.items()}
  frames=re.findall(r'File "[^"\n]*/backend/api/([a-z_]+\.py)", line (\d+), in ([A-Za-z_][A-Za-z_0-9]*)',text)
  status=row.get('httpRequest',{}).get('status')
  if isinstance(status,int) and not isinstance(status,bool):matches['http_status']=status
  latency=row.get('httpRequest',{}).get('latency','')
  if isinstance(latency,str) and re.fullmatch(r'\d+(?:\.\d+)?s',latency):matches['http_latency_seconds']=float(latency[:-1])
  request_path=urlsplit(row.get('httpRequest',{}).get('requestUrl','')).path
  if request_path in {'/api/payments/checkout','/api/health','/ready','/api/live'}:matches['request_route']=request_path
  elif re.fullmatch(r'/api/events/[^/]+/venue/booking',request_path):matches['request_route']='/api/events/[id]/venue/booking'
  if frames:matches['backend_frames']=[{'file':f,'line':int(n),'function':fn} for f,n,fn in frames]
  statements=re.findall(r'\[SQL: (SELECT|UPDATE|INSERT INTO|DELETE FROM)\s+([a-z_]+)',text)
  if statements:matches['statement_kinds']=[{'operation':op,'relation':table} for op,table in statements]
  # PostgreSQL emits the failed SQL separately from the ERROR record. Export
  # only fixed probe categories, never SQL text or any bound account values.
  probes={
   'users_schema':r'\bSELECT\s+1\s+FROM\s+users\s+LIMIT\s+1\b',
   'postgis_extension':r'\bSELECT\s+PostGIS_Version\s*\(\s*\)',
   'connection_ping':r'\bSTATEMENT:\s*SELECT\s+1\s*;?\s*$',
  }
  identified=[name for name,pattern in probes.items() if re.search(pattern,text,re.I)]
  if identified:matches['readiness_probes']=identified
  result.append({'timestamp':row.get('timestamp'),'severity':row.get('severity'),'signals':{k:v for k,v in matches.items() if v}})
 return result

def movement_timings(rows):
 result=[]
 allowed={'authentication_ms','context_ms','simulation_ms','commit_and_publish_ms','queue_ms','flush_ms',
          'connection_ms','sql_ms','sql_max_ms','sql_count','thread_cpu_ms','gc_overlap_ms'}
 for row in rows:
  text=row.get('textPayload','')+' '+str(row.get('jsonPayload',{}).get('message',''))
  if 'movement_transaction_timing ' not in text:continue
  payload=text.split('movement_transaction_timing ',1)[1].strip()
  try:value=json.loads(payload)
  except (ValueError,TypeError):continue
  if not isinstance(value,dict):continue
  phases={k:v for k,v in value.items() if k in allowed and type(v) in (int,float) and 0<=v<=120000}
  if phases:result.append({'timestamp':row.get('timestamp'),'phases_ms':phases})
 return result

def run(c,sha):
 release=c.get_json(f'releases/{sha}/staging.json')
 if not release or release.get('sha')!=sha:raise Blocked('Exact staging release required')
 current=ready_service(c,'mindaam-staging')
 if current['status']['latestReadyRevisionName']!=release['revision'] or current['spec']['template']['spec']['containers'][0]['image']!=release['image']:
  raise Blocked('Refuse diagnostics for a stale staging release')
 start=datetime.datetime.fromtimestamp(release['deployed_at'],datetime.timezone.utc).isoformat()
 end=datetime.datetime.now(datetime.timezone.utc).isoformat()
 query=f'resource.type="cloud_run_revision" AND resource.labels.service_name="mindaam-staging" AND resource.labels.revision_name="{release["revision"]}" AND timestamp>="{start}" AND severity>=ERROR'
 rows=c.gc('logging','read',query,'--limit=200','--format=json(timestamp,severity,textPayload,jsonPayload.message,httpRequest.status,httpRequest.requestUrl,httpRequest.latency)')
 result={'sha':sha,'revision':release['revision'],'read_only':True,'release_approval':False,'error_log_limit':200,'errors':summarize(rows),'metrics':{}}
 timing_query=f'resource.type="cloud_run_revision" AND resource.labels.service_name="mindaam-staging" AND resource.labels.revision_name="{release["revision"]}" AND timestamp>="{start}" AND (textPayload:"movement_transaction_timing " OR jsonPayload.message:"movement_transaction_timing ")'
 result['movement_timings']=movement_timings(c.gc('logging','read',timing_query,'--limit=200','--format=json(timestamp,textPayload,jsonPayload.message)'))
 # Readiness deliberately returns a generic dependency error. Correlate it
 # with server-side PostgreSQL errors without exporting SQL, identities or
 # connection strings from the shared instance's raw log payloads.
 database_query=(f'resource.type="cloudsql_database" AND resource.labels.database_id="{c.project}:mindaam-postgres" '
                 f'AND timestamp>="{start}" AND timestamp<="{end}" '
                 'AND (severity>=ERROR OR textPayload=~"(?i)(error|fatal|panic|timeout|deadlock|statement:)")')
 database_rows=c.gc('logging','read',database_query,'--limit=200','--format=json(timestamp,severity,textPayload,jsonPayload.message)')
 result['database_errors']=summarize(database_rows)
 token=command(['gcloud','auth','print-access-token'],sensitive=True)
 # A release-age window can fill the first API page with a single series,
 # silently omitting other databases/memory components. Use a bounded recent
 # window for correlation with the targeted reproduction; retain log history.
 metric_start=max(start,(datetime.datetime.fromisoformat(end)-datetime.timedelta(hours=1)).isoformat())
 result['metric_window']={'start':metric_start,'end':end}
 for metric in ['cloudsql.googleapis.com/database/postgresql/num_backends','cloudsql.googleapis.com/database/cpu/utilization','cloudsql.googleapis.com/database/memory/components','cloudsql.googleapis.com/database/disk/read_ops_count','cloudsql.googleapis.com/database/disk/write_ops_count','run.googleapis.com/container/memory/utilizations','run.googleapis.com/container/cpu/utilizations']:
  scope=f'resource.labels.database_id="{c.project}:mindaam-postgres"' if metric.startswith('cloudsql.') else f'resource.labels.revision_name="{release["revision"]}"'
  params={'filter':f'metric.type="{metric}" AND {scope}','interval.startTime':metric_start,'interval.endTime':end,'pageSize':1000}
  data=get_json('https://monitoring.googleapis.com/v3/projects/'+c.project+'/timeSeries?'+urlencode(params),token,c.project)
  if data.get('nextPageToken'):raise Blocked('Diagnostic metric window exceeds bounded page; do not interpret partial series')
  result['metrics'][metric]=data
 from staging_pool_probe import collect
 result['pool_activity']=collect(c,release)
 result['pool_probe_cleanup']=True
 Path('gcp-evidence').mkdir(exist_ok=True)
 Path('gcp-evidence/staging-diagnostics.json').write_text(json.dumps(result,indent=2))
 print('Exact staging error categories and numeric resource evidence collected; no log payloads exported.')
