"""Root-owned VM reconciler. Only private release objects and scoped secrets are read."""
import base64
import hashlib
import datetime
import json
import os
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


def metadata(path):
    req = urllib.request.Request("http://metadata.google.internal/computeMetadata/v1/" + path, headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode()


def fetch(url, payload=None):
    token = json.loads(metadata("instance/service-accounts/default/token"))["access_token"]
    req = urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode(), headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def measurements(project):
    memory = {line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines()}
    value = 1 - memory["MemAvailable"] / memory["MemTotal"]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    fetch(f"https://monitoring.googleapis.com/v3/projects/{project}/timeSeries", {"timeSeries": [{
        "metric": {"type": "custom.googleapis.com/mindaam/host_memory_utilization"},
        "resource": {"type": "global", "labels": {"project_id": project}},
        "metricKind": "GAUGE", "valueType": "DOUBLE",
        "points": [{"interval": {"endTime": now}, "value": {"doubleValue": value}}]}]})


def main():
    os.umask(0o077)
    project = metadata("project/project-id")
    try:
        measurements(project)
    except Exception:
        print("Mindaam monitoring delivery failed; application reconciliation continues.")
    bucket = project + "-releases"
    def obj(key):
        return fetch(f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{urllib.parse.quote(key, safe='')}?alt=media")
    descriptor = json.loads(obj("vm/current.json"))
    marker = Path("/var/lib/mindaam/applied-bundle")
    if marker.exists() and marker.read_text() == descriptor["sha256"] and Path("/run/mindaam/compose.json").exists():
        return  # No repeated secret access or container restarts between releases.
    archive = obj(descriptor["object"])
    if hashlib.sha256(archive).hexdigest() != descriptor["sha256"]:
        raise RuntimeError("VM bundle integrity mismatch")
    target = Path("/opt/mindaam/config")
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile() as f:
        f.write(archive); f.flush()
        with tarfile.open(f.name) as tar:
            allowed = {"common.py", "render.py", "settings.json", "deployment.json", "vm_agent.py"}
            if {m.name for m in tar.getmembers()} != allowed or any(not m.isfile() for m in tar.getmembers()):
                raise RuntimeError("Unexpected VM bundle members")
            tar.extractall(target, filter="data")
    Path("/opt/mindaam/agent.py").write_bytes((target / "vm_agent.py").read_bytes())
    import sys
    sys.path.insert(0, str(target))
    from render import compose_config, caddy_config, livekit_config
    from common import SETTINGS
    def secret(name):
        data = json.loads(fetch(f"https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{name}/versions/latest:access"))
        return base64.b64decode(data["payload"]["data"]).decode()
    config = json.loads((target / "deployment.json").read_text())
    keys = {secret(f"mindaam-{e}-livekit-key"): secret(f"mindaam-{e}-livekit-secret") for e in ("staging", "production")}
    redis = "\n".join(["bind 127.0.0.1 " + SETTINGS["media_private_ip"], "port 6379", "protected-mode yes",
                       "requirepass " + secret("mindaam-redis-password"), "maxmemory 128mb", "maxmemory-policy noeviction",
                       'save ""', "appendonly no", "loglevel warning", ""])
    files = {"livekit.json": json.dumps(livekit_config(keys)), "caddy.json": json.dumps(caddy_config(config.get("production_origin"))),
             "redis.conf": redis, "compose.json": json.dumps(compose_config())}
    run = Path("/run/mindaam"); run.mkdir(exist_ok=True, mode=0o700)
    changed = set()
    for name, content in files.items():
        dest = run / name
        if not dest.exists() or dest.read_text() != content:
            dest.write_text(content); dest.chmod(0o600); changed.add(name)
    Path("/var/lib/mindaam/caddy").mkdir(parents=True, exist_ok=True)
    base = ["docker", "compose", "-p", "mindaam", "-f", str(run / "compose.json")]
    subprocess.run(base + ["up", "-d", "--remove-orphans"], check=True, stdout=subprocess.DEVNULL)
    # Caddy can reload HTTPS routing without interrupting existing media rooms.
    if "caddy.json" in changed:
        subprocess.run(base + ["exec", "-T", "caddy", "caddy", "reload", "--config", "/run/mindaam/caddy.json"], check=True, stdout=subprocess.DEVNULL)
    # Existing key/Redis changes require a controlled restart; ordinary deploys do not.
    for file, service in [("redis.conf", "redis"), ("livekit.json", "livekit")]:
        if file in changed:
            subprocess.run(base + ["restart", service], check=True, stdout=subprocess.DEVNULL)
    Path("/var/lib/mindaam/applied-bundle").write_text(descriptor["sha256"])


if __name__ == "__main__":
    main()
