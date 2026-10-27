"""Bounded retries for read-only readiness, never retry mutations or credentials."""
import json
import socket
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from common import Blocked


def read_url(url, *, timeout=180, json_body=False):
    deadline = time.monotonic() + timeout
    delay = 2
    reason = 'not ready'
    while True:
        try:
            with urlopen(url, timeout=min(15, max(1, deadline - time.monotonic()))) as response:
                body = response.read().decode()
            return json.loads(body) if json_body else body
        except HTTPError as error:
            # Public invocation can briefly return 403/404 after IAM/revision updates.
            if error.code not in (403, 404, 408, 429, 500, 502, 503, 504):
                raise Blocked(f'Readiness HTTP {error.code}: {url}') from None
            reason = f'HTTP {error.code}'
        except (URLError, TimeoutError, socket.timeout, ssl.SSLError):
            reason = 'DNS/TLS/connection unavailable'
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise Blocked('Malformed readiness response: ' + url) from None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise Blocked(f'Readiness deadline ({timeout}s): {url}: {reason}')
        time.sleep(min(delay, remaining)); delay = min(delay * 2, 15)


def ready_service(c, name, *, timeout=180):
    deadline = time.monotonic() + timeout
    while True:
        service = c.gc('run', 'services', 'describe', name, '--region=' + c.region)
        c.owned(service.get('metadata', {}), name)
        status = service.get('status', {})
        ready = next((x for x in status.get('conditions', []) if x.get('type') == 'Ready'), {})
        generation = int(service.get('metadata', {}).get('generation', 0))
        observed = int(status.get('observedGeneration', 0))
        if (ready.get('status') == 'True' and observed >= generation
                and status.get('latestReadyRevisionName') == status.get('latestCreatedRevisionName')
                and status.get('latestReadyRevisionName') and status.get('url')):
            return service
        if ready.get('status') == 'False':
            raise Blocked('Cloud Run revision failed readiness: ' + name + ': ' + ready.get('reason', 'unknown'))
        if time.monotonic() >= deadline:
            raise Blocked('Cloud Run revision readiness timed out: ' + name)
        time.sleep(5)


def ready_tls(host, *, timeout=180):
    deadline = time.monotonic() + timeout
    while True:
        try:
            with socket.create_connection((host, 443), timeout=15) as raw:
                with ssl.create_default_context().wrap_socket(raw, server_hostname=host) as tls:
                    tls.getpeercert()  # keep certificate chain and hostname verification enabled
            return
        except (OSError, ssl.SSLError):
            if time.monotonic() >= deadline:
                raise Blocked('DNS/TLS readiness deadline: ' + host) from None
            time.sleep(min(5, max(0, deadline - time.monotonic())))
