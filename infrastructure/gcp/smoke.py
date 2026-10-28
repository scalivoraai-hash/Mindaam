"""Read-only real-URL checks. A container or workflow alone cannot produce PASS."""
import json
import ssl
import socket
import time
from urllib.request import urlopen
from urllib.parse import urlsplit
from common import SETTINGS, Blocked
from readiness import read_url, ready_tls


def check(release):
    origin = release["origin"]
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not (parsed.hostname == SETTINGS["domain"] or (parsed.hostname or "").endswith(".run.app")):
        raise Blocked("Refusing an unexpected application origin")
    start = time.monotonic()
    health = read_url(origin + "/api/health", json_body=True)
    if health.get("status") != "ready" or health.get("environment") != release["environment"]:
        raise Blocked("Actual deployed health/environment failed")
    if release.get('profile') == 'limited-public-beta-v1':
        config = read_url(origin + '/api/config', json_body=True)
        if config.get('flags', {}).get('payment_actions_enabled') is not False or config['flags'].get('payments_enabled') is not False:
            raise Blocked('Public-beta payment actions are not gated on the actual service')
    html = read_url(origin)
    if "Mindaam" not in html:
        raise Blocked("Mindaam page was not served")
    for host in (SETTINGS["media_domain"], SETTINGS["turn_domain"]):
        ready_tls(host)
    return {"health": health, "origin": origin, "elapsed_seconds": round(time.monotonic() - start, 3), "tls": True}


if __name__ == "__main__":
    from pathlib import Path
    result = check(json.loads(Path("deployment-result.json").read_text()))
    Path("smoke-result.json").write_text(json.dumps(result, indent=2))
    print("Actual URL smoke checks passed: " + result["origin"])
