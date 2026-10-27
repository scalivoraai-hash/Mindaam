"""Read-only production cutover verification. Never changes DNS or deploys."""
import json
import socket
import time
from pathlib import Path
from common import Blocked, SETTINGS
from readiness import ready_service
from smoke import check


def finalize(c, sha):
    release = c.get_json(f'releases/{sha}/production.json')
    provider = c.get_json(f'releases/{sha}/production-provider-verified.json')
    if (not release or not provider or release.get('sha') != sha or release.get('environment') != 'production'
            or any(provider.get(k) != release.get(k) for k in ('sha', 'image', 'revision', 'origin', 'provider_origin'))):
        raise Blocked('Complete this exact production release before DNS verification')
    current = ready_service(c, 'mindaam-production')
    if (current['status']['url'] != release['provider_origin']
            or current['status']['latestReadyRevisionName'] != release['revision']
            or current['spec']['template']['spec']['containers'][0]['image'] != release['image']):
        raise Blocked('Production image/revision changed; refuse stale cutover evidence')
    expected = c.get_json('foundation.json')['media_ip']
    deadline = time.monotonic() + 180
    while True:
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(SETTINGS['domain'], 443, type=socket.SOCK_STREAM)}
        except socket.gaierror:
            addresses = set()
        if addresses == {expected}:
            break
        if time.monotonic() >= deadline:
            raise Blocked('Apex DNS must resolve exclusively to the reserved media IP; inspect A/AAAA/forwarding')
        time.sleep(10)
    result = {**release, 'verified_at': int(time.time()), 'smoke': check(release),
              'provider_smoke': check({**release, 'origin': release['provider_origin']})}
    c.put_json(f'releases/{sha}/production-verified.json', result)
    Path('deployment-result.json').write_text(json.dumps(release, indent=2))
    Path('smoke-result.json').write_text(json.dumps(result, indent=2))
    print('Production HTTPS cutover verified: ' + release['origin'])
