"""Read-only, exact-revision failure evidence. Never exports log payloads or secrets."""
import datetime,json,re
from urllib.parse import urlsplit
from pathlib import Path
from common import Blocked,command
from readiness import ready_service
from diagnostics import get_json
from urllib.parse import urlencode

PATTERNS={
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
  request_path=urlsplit(row.get('httpRequest',{}).get('requestUrl','')).path
  if request_path in {'/api/payments/checkout','/api/health','/ready','/api/live'}:matches['request_route']=request_path
  elif re.fullmatch(r'/api/events/[^/]+/venue/booking',request_path):matches['request_route']='/api/events/[id]/venue/booking'
  if frames:matches['backend_frames']=[{'file':f,'line':int(n),'function':fn} for f,n,fn in frames]
  statements=re.findall(r'\[SQL: (SELECT|UPDATE|INSERT INTO|DELETE FROM)\s+([a-z_]+)',text)
  if statements:matches['statement_kinds']=[{'operation':op,'relation':table} for op,table in statements]
  result.append({'timestamp':row.get('timestamp'),'severity':row.get('severity'),'signals':{k:v for k,v in matches.items() if v}})
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
 rows=c.gc('logging','read',query,'--limit=200','--format=json(timestamp,severity,textPayload,jsonPayload.message,httpRequest.status,httpRequest.requestUrl)')
 result={'sha':sha,'revision':release['revision'],'read_only':True,'release_approval':False,'error_log_limit':200,'errors':summarize(rows),'metrics':{}}
 token=command(['gcloud','auth','print-access-token'],sensitive=True)
 for metric in ['cloudsql.googleapis.com/database/postgresql/num_backends','cloudsql.googleapis.com/database/cpu/utilization','cloudsql.googleapis.com/database/memory/components','run.googleapis.com/container/memory/utilizations','run.googleapis.com/container/cpu/utilizations']:
  scope=f'resource.labels.database_id="{c.project}:mindaam-postgres"' if metric.startswith('cloudsql.') else f'resource.labels.revision_name="{release["revision"]}"'
  params={'filter':f'metric.type="{metric}" AND {scope}','interval.startTime':start,'interval.endTime':end,'pageSize':1000}
  data=get_json('https://monitoring.googleapis.com/v3/projects/'+c.project+'/timeSeries?'+urlencode(params),token,c.project)
  result['metrics'][metric]=data
 Path('gcp-evidence').mkdir(exist_ok=True)
 Path('gcp-evidence/staging-diagnostics.json').write_text(json.dumps(result,indent=2))
 print('Exact staging error categories and numeric resource evidence collected; no log payloads exported.')
