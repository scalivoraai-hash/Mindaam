"""Read-only production incident evidence. Never exports request queries or payloads."""
import datetime
import json
from pathlib import Path
from urllib.parse import urlsplit
from common import Blocked
from readiness import ready_service
from staging_diagnostics import summarize

# Export only known public route names; never account IDs, emails or query strings.
PUBLIC_PATHS = {'/', '/api/health', '/health', '/ready', '/api/auth/login',
                '/api/auth/register', '/api/auth/me', '/api/cities', '/api/world/enter'}

def request_summary(rows):
    result = []
    for row in rows:
        request = row.get('httpRequest', {})
        path = urlsplit(request.get('requestUrl', '')).path
        result.append({'timestamp': row.get('timestamp'),
                       'revision': row.get('resource', {}).get('labels', {}).get('revision_name'),
                       'status': request.get('status'),
                       'method': request.get('requestMethod'),
                       'path': path if path in PUBLIC_PATHS else '[other route]',
                       'latency': request.get('latency')})
    return result

def run(c, sha):
    if c.project != 'mindaam':
        raise Blocked('Production diagnostics restricted to Mindaam')
    current = ready_service(c, 'mindaam-production')
    end = datetime.datetime.now(datetime.timezone.utc)
    start = (end - datetime.timedelta(days=7)).isoformat()
    scope = ('resource.type="cloud_run_revision" AND '
             'resource.labels.service_name="mindaam-production" AND '
             f'timestamp>="{start}"')
    requests = c.gc('logging', 'read', scope + ' AND httpRequest.status>=500',
                    '--limit=500', '--format=json(timestamp,resource.labels.revision_name,httpRequest.status,httpRequest.requestMethod,httpRequest.requestUrl,httpRequest.latency)')
    errors = c.gc('logging', 'read', scope + ' AND severity>=ERROR',
                  '--limit=200', '--format=json(timestamp,severity,textPayload,jsonPayload.message)')
    result = {'read_only': True, 'release_approval': False, 'requested_sha': sha,
              'observed_at': end.isoformat(), 'window_start': start,
              'revision': current['status']['latestReadyRevisionName'],
              'image': current['spec']['template']['spec']['containers'][0]['image'],
              'traffic': current['status'].get('traffic', []),
              'request_limit': 500, 'requests': request_summary(requests),
              'error_limit': 200, 'errors': summarize(errors)}
    Path('gcp-evidence').mkdir(exist_ok=True)
    Path('gcp-evidence/production-diagnostics.json').write_text(json.dumps(result, indent=2))
    print('Read-only production revision, 5xx routes and sanitized exception categories collected.')
