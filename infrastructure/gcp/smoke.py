"""Read-only real-URL checks. A container or workflow alone cannot produce PASS."""
import json
import ssl
import socket
import time
from urllib.request import urlopen
from urllib.parse import urlsplit
from common import SETTINGS, Blocked


def check(release):
    origin = release["origin"]
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not (parsed.hostname == SETTINGS["domain"] or parsed.hostname.endswith(".run.app")):
        raise Blocked("Refusing an unexpected application origin")
    start = time.monotonic()
    with urlopen(origin + "/api/health", timeout=120) as r:
        health = json.load(r)
    if health.get("status") != "ready" or health.get("environment") != release["environment"]:
        raise Blocked("Actual deployed health/environment failed")
    with urlopen(origin, timeout=60) as r:
        html = r.read().decode()
    if "Mindaam" not in html:
        raise Blocked("Mindaam page was not served")
    for host in (SETTINGS["media_domain"], SETTINGS["turn_domain"]):
        with socket.create_connection((host, 443), timeout=20) as raw:
            with ssl.create_default_context().wrap_socket(raw, server_hostname=host) as tls:
                tls.getpeercert()  # verifies chain and hostname, never bypass TLS verification
    return {"health": health, "origin": origin, "elapsed_seconds": round(time.monotonic() - start, 3), "tls": True}


if __name__ == "__main__":
    from pathlib import Path
    result = check(json.loads(Path("deployment-result.json").read_text()))
    Path("smoke-result.json").write_text(json.dumps(result, indent=2))
    print("Actual URL smoke checks passed: " + result["origin"])
