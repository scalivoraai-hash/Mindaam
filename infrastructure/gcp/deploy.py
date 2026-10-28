"""Resumable Mindaam-only provisioning and release operations. Never destroys resources."""
import argparse
import datetime
import base64
import hashlib
import io
import json
import math
import os
import re
import secrets
import tarfile
import tempfile
import time
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from common import Cloud, Blocked, SETTINGS, HERE, LABELS, command, summary
from render import service, postgres
from readiness import ready_service

DESCRIPTION = "Managed by Mindaam GitHub"
OPTIONAL = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM",
            "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_SUBSCRIPTION_WEBHOOK_SECRET",
            "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]


def ensure(c, describe, create, *, name, labels=True):
    current = c.gc(*describe, missing=True)
    if current is not None:
        if labels:
            c.owned(current, name)
        elif current.get("description") != DESCRIPTION:
            raise Blocked("Refusing to adopt unrelated resource " + name)
        return current
    c.gc(*create)
    return c.gc(*describe)


def bucket(c, name):
    resource = c.gc("storage", "buckets", "describe", "gs://" + name, missing=True)
    if resource is None:
        c.gc("storage", "buckets", "create", "gs://" + name, "--location=" + c.region,
             "--uniform-bucket-level-access", "--public-access-prevention")
        c.gc("storage", "buckets", "update", "gs://" + name, "--update-labels=" + LABELS, "--versioning")
    else:
        c.owned(resource, name)
    c.gc("storage", "buckets", "update", "gs://" + name, "--uniform-bucket-level-access", "--public-access-prevention")
    lifecycle = {"rule": [{"action": {"type": "Delete"}, "condition": {"daysSinceNoncurrentTime": 7, "numNewerVersions": 3}}]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as f:
        json.dump(lifecycle, f); f.flush()
        c.gc("storage", "buckets", "update", "gs://" + name, "--lifecycle-file=" + f.name)


def bootstrap_secrets(c):
    token = lambda: secrets.token_urlsafe(36)
    c.secret("mindaam-postgres-password", generate=token)
    c.secret("mindaam-redis-password", generate=token, readers=[c.sa("media")])
    pg = c.secret_value("mindaam-postgres-password")
    redis = c.secret_value("mindaam-redis-password")
    connection = f"{c.project}:{c.region}:mindaam-postgres"
    for index, env in enumerate(("staging", "production")):
        prefix = "mindaam-" + env + "-"
        runtime, migrator = c.sa(env), c.sa("migrate")
        c.secret(prefix + "database-password", generate=token)
        password = c.secret_value(prefix + "database-password")
        database = "mindaam_" + env
        c.secret(prefix + "database-url", generate=lambda: f"postgresql+psycopg://{database}:{quote(password, safe='')}@/{database}?host=/cloudsql/{connection}", readers=[runtime, migrator])
        c.secret(prefix + "migration-url", generate=lambda: f"postgresql+psycopg://postgres:{quote(pg, safe='')}@/{database}?host=/cloudsql/{connection}", readers=[migrator])
        c.secret(prefix + "redis-url", generate=lambda: f"redis://:{quote(redis, safe='')}@{SETTINGS['media_private_ip']}:6379/{index}", readers=[runtime])
        for suffix, generator, readers in [
            ("livekit-key", lambda: "MK" + secrets.token_hex(12), [runtime, c.sa("media")]),
            ("livekit-secret", token, [runtime, c.sa("media")]),
            ("pulsepoint-secret", token, [runtime]),
            ("mail-encryption-key", lambda: base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(), [runtime]),
            ("owner-email", lambda: SETTINGS["owner_email"], [runtime]),
            ("owner-username", lambda: "mindaam_owner", [runtime]),
            ("owner-password", token, [runtime])]:
            c.secret(prefix + suffix, generate=generator, readers=readers)
        for key in OPTIONAL:
            name = prefix + key.lower().replace("_", "-")
            existing = c.gc("secrets", "describe", name, missing=True)
            if existing is None:
                c.gc("secrets", "create", name, "--replication-policy=automatic", "--labels=" + LABELS)
            else:
                c.owned(existing, name)
            c.gc("secrets", "add-iam-policy-binding", name, "--member=serviceAccount:" + runtime, "--role=roles/secretmanager.secretAccessor", raw=True)


def vm_bundle(c, production_origin=None):
    previous = c.get_json("vm/current.json")
    if production_origin is None and previous:
        production_origin = previous.get("production_origin")
    content = {name: (HERE / name).read_bytes() for name in ("common.py", "render.py", "settings.json", "vm_agent.py")}
    content["deployment.json"] = json.dumps({"production_origin": production_origin}).encode()
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as tar:
        for name, value in sorted(content.items()):
            member = tarfile.TarInfo(name); member.size = len(value); member.mode = 0o600
            tar.addfile(member, io.BytesIO(value))
    digest = hashlib.sha256(data.getvalue()).hexdigest()
    key = "vm/bundles/" + digest + ".tar"
    with tempfile.NamedTemporaryFile() as f:
        f.write(data.getvalue()); f.flush()
        c.gc("storage", "cp", f.name, f"gs://{c.bucket}/{key}", raw=True)
    c.put_json("vm/current.json", {"object": key, "sha256": digest, "production_origin": production_origin})


def startup_script():
    agent = base64.b64encode((HERE / "vm_agent.py").read_bytes()).decode()
    return """#!/bin/bash
set -euo pipefail
umask 077
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends docker.io docker-compose-v2 python3
systemctl enable --now docker
install -d -m 700 /opt/mindaam /var/lib/mindaam /run/mindaam
base64 -d > /opt/mindaam/agent.py <<'AGENT'
""" + agent + """
AGENT
cat > /etc/systemd/system/mindaam-reconcile.service <<'UNIT'
[Unit]
Description=Mindaam scoped configuration and monitoring
After=network-online.target docker.service
Wants=network-online.target
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/mindaam/agent.py
TimeoutStartSec=240
UNIT
cat > /etc/systemd/system/mindaam-reconcile.timer <<'UNIT'
[Unit]
Description=Resume Mindaam configuration after DNS/setup changes
[Timer]
OnBootSec=15
OnUnitActiveSec=60
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now mindaam-reconcile.timer
"""


def ensure_postgres(c):
    existing = c.gc("sql", "instances", "describe", "mindaam-postgres", missing=True)
    if existing is not None:
        c.owned(existing, "PostgreSQL")
    else:
        token = command(["gcloud", "auth", "print-access-token"], sensitive=True)
        request = Request(f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{c.project}/instances",
                          data=json.dumps(postgres(c)).encode(),
                          headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=60) as response:
                operation = json.load(response)
        except HTTPError as error:
            # Payload has configuration only, but never echo authorization headers.
            raise Blocked("Cloud SQL create failed: HTTP " + str(error.code)) from None
        c.gc("sql", "operations", "wait", operation["name"], "--timeout=3600")
    # A stopped workflow may leave the creation operation running; wait, don't duplicate.
    pending = c.gc("sql", "operations", "list", "--instance=mindaam-postgres", "--filter=status!=DONE") or []
    for operation in pending:
        c.gc("sql", "operations", "wait", operation["name"], "--timeout=3600")
    current = c.gc("sql", "instances", "describe", "mindaam-postgres")
    c.owned(current, "PostgreSQL")
    if current.get("state") != "RUNNABLE":
        raise Blocked("Cloud SQL is not ready; inspect the recorded operation and resume foundation")
    return current


def firewall_ports(entries):
    """Compare effective TCP/UDP access, including repeated protocol entries."""
    ports = {}
    for entry in entries:
        protocol = {'6': 'tcp', '17': 'udp'}.get(entry['IPProtocol'], entry['IPProtocol'])
        if protocol not in ('tcp', 'udp') or not entry.get('ports'):
            raise Blocked('Unexpected protocol or unrestricted ports in firewall')
        for value in entry['ports']:
            if not isinstance(value, str) or not re.fullmatch(r'\d{1,5}(?:-\d{1,5})?', value):
                raise Blocked('Invalid firewall port range')
            bounds = [int(v) for v in value.split('-')]
            first, last = bounds[0], bounds[-1]
            if not 0 <= first <= last <= 65535:
                raise Blocked('Invalid firewall port range')
            ports.setdefault(protocol, set()).update(range(first, last + 1))
    return ports


def validate_firewall(c, firewall, name, allow, source):
    expected = [{'IPProtocol': entry.split(':')[0], 'ports': [entry.split(':')[1]]}
                for entry in allow.split(',')]
    network = f'https://www.googleapis.com/compute/v1/projects/{c.project}/global/networks/mindaam'
    if (firewall.get('description') != DESCRIPTION
            or firewall.get('network') != network
            or firewall_ports(firewall.get('allowed', [])) != firewall_ports(expected)
            or set(firewall.get('sourceRanges', [])) != {source}
            or set(firewall.get('targetServiceAccounts', [])) != {c.sa('media')}
            or firewall.get('direction') != 'INGRESS'
            or firewall.get('disabled', False) is not False
            or any(firewall.get(key) for key in ('sourceTags', 'sourceServiceAccounts', 'targetTags', 'denied'))):
        raise Blocked('Existing firewall drifted from the restricted startup policy: ' + name)


def foundation(c):
    c.require_project()
    if os.getenv("MINDAAM_BUDGET_CONFIRMED") != "true":
        raise Blocked("Project budget alerts must be confirmed by bootstrap before paid resources are created.")
    bucket(c, c.bucket)
    bucket(c, c.assets)  # private immutable asset/archive preparation; current small assets stay in the app cache
    ensure(c, ["artifacts", "repositories", "describe", "mindaam", "--location=" + c.region],
           ["artifacts", "repositories", "create", "mindaam", "--repository-format=docker", "--location=" + c.region, "--labels=" + LABELS], name="mindaam")
    cleanup = [{"name": "delete-untagged", "action": {"type": "Delete"}, "condition": {"tagState": "untagged", "olderThan": "604800s"}},
               {"name": "keep-recent", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 5}}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as f:
        json.dump(cleanup, f); f.flush()
        c.gc("artifacts", "repositories", "set-cleanup-policies", "mindaam", "--location=" + c.region, "--policy=" + f.name, "--no-dry-run")
    ensure(c, ["compute", "networks", "describe", "mindaam"],
           ["compute", "networks", "create", "mindaam", "--subnet-mode=custom", "--description=" + DESCRIPTION], name="mindaam network", labels=False)
    subnet = ensure(c, ["compute", "networks", "subnets", "describe", "mindaam-run", "--region=" + c.region],
                    ["compute", "networks", "subnets", "create", "mindaam-run", "--region=" + c.region, "--network=mindaam", "--range=" + SETTINGS["subnet_cidr"], "--enable-private-ip-google-access", "--description=" + DESCRIPTION], name="mindaam-run", labels=False)
    if subnet["ipCidrRange"] != SETTINGS["subnet_cidr"]:
        raise Blocked("Unexpected existing subnet range")
    for name, allow, source in [("mindaam-media-public", "tcp:80,tcp:443,tcp:7881,udp:3478,udp:50000-50200", "0.0.0.0/0"),
                                ("mindaam-redis-private", "tcp:6379", SETTINGS["subnet_cidr"])]:
        firewall = ensure(c, ["compute", "firewall-rules", "describe", name],
               ["compute", "firewall-rules", "create", name, "--network=mindaam", "--allow=" + allow,
                "--source-ranges=" + source, "--target-service-accounts=" + c.sa("media"), "--description=" + DESCRIPTION], name=name, labels=False)
        validate_firewall(c, firewall, name, allow, source)
    address = ensure(c, ["compute", "addresses", "describe", "mindaam-media", "--region=" + c.region],
                     ["compute", "addresses", "create", "mindaam-media", "--region=" + c.region, "--description=" + DESCRIPTION], name="media IP", labels=False)
    bootstrap_secrets(c)
    instance = ensure_postgres(c)
    sql_settings = instance["settings"]
    if (sql_settings["tier"] != SETTINGS["sql_tier"] or sql_settings.get("availabilityType") != "ZONAL"
            or int(sql_settings.get("dataDiskSizeGb", 0)) > SETTINGS["sql_disk_limit_gb"]
            or int(sql_settings.get("storageAutoResizeLimit", 0)) != SETTINGS["sql_disk_limit_gb"]
            or not sql_settings.get("backupConfiguration", {}).get("enabled")
            or sql_settings.get("ipConfiguration", {}).get("authorizedNetworks")):
        raise Blocked("Unexpected SQL size or public authorized networks; review before proceeding.")
    c.file_command(["sql", "users", "set-password", "postgres", "--instance=mindaam-postgres"], {"--password": c.secret_value("mindaam-postgres-password")}, sensitive=True)
    for env in ("staging", "production"):
        name = "mindaam_" + env
        if c.gc("sql", "databases", "describe", name, "--instance=mindaam-postgres", missing=True) is None:
            c.gc("sql", "databases", "create", name, "--instance=mindaam-postgres")
    c.gc("storage", "buckets", "add-iam-policy-binding", "gs://" + c.bucket,
         "--member=serviceAccount:" + c.sa("media"), "--role=roles/storage.objectViewer",
         "--condition=title=mindaam-vm-only,expression=resource.name.startsWith('projects/_/buckets/" + c.bucket + "/objects/vm/')", raw=True)
    vm_bundle(c)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh") as f:
        f.write(startup_script()); f.flush()
        vm = ensure(c, ["compute", "instances", "describe", "mindaam-media", "--zone=" + c.zone],
                    ["compute", "instances", "create", "mindaam-media", "--zone=" + c.zone, "--machine-type=" + SETTINGS["vm_type"],
                     "--subnet=mindaam-run", "--private-network-ip=" + SETTINGS["media_private_ip"], "--address=" + address["address"],
                     "--image-family=ubuntu-2404-lts-amd64", "--image-project=ubuntu-os-cloud", "--boot-disk-type=pd-standard",
                     "--boot-disk-size=" + str(SETTINGS["vm_disk_gb"]), "--service-account=" + c.sa("media"), "--scopes=cloud-platform",
                     "--labels=" + LABELS, "--deletion-protection", "--shielded-secure-boot", "--shielded-vtpm", "--shielded-integrity-monitoring",
                     "--metadata=enable-oslogin=TRUE,block-project-ssh-keys=TRUE", "--metadata-from-file=startup-script=" + f.name], name="media VM")
    if not vm["machineType"].endswith("/" + SETTINGS["vm_type"]):
        raise Blocked("Existing VM differs from the approved startup size.")
    inventory = {"project": c.project, "region": c.region, "zone": c.zone, "media_ip": address["address"],
                 "vm": SETTINGS["vm_type"], "sql": SETTINGS["sql_tier"], "sql_disk_limit_gb": SETTINGS["sql_disk_limit_gb"],
                 "cloud_run_max": {e: SETTINGS[e + "_max_instances"] for e in ("staging", "production")}, "created_at": int(time.time())}
    c.put_json("foundation.json", inventory)
    summary("Foundation reconciled. DNS records (DNS-only, no HTTP proxy):\n\n" + "\n".join(
        f"- A `{domain}` → `{address['address']}`" for domain in [SETTINGS["media_domain"], SETTINGS["turn_domain"]]) + "\n\nDo not redirect the old Railway domain.")


def image_check(c, image):
    if not re.fullmatch(re.escape(c.region + "-docker.pkg.dev/" + c.project + "/mindaam/app@sha256:") + r"[0-9a-f]{64}", image):
        raise Blocked("Use the immutable image digest from this project's Artifact Registry.")


def migrate(c, env, image):
    # Back up the actual existing target before any migration; no rollback/downgrade.
    if env == "production":
        c.gc("sql", "backups", "create", "--instance=mindaam-postgres", "--description=Mindaam pre-release backup")
    name = "mindaam-migrate-" + env
    existing = c.gc("run", "jobs", "describe", name, "--region=" + c.region, missing=True)
    if existing is not None:
        c.owned(existing.get("metadata", {}), name)
    args = ["run", "jobs", "deploy", name, "--region=" + c.region, "--image=" + image,
            "--service-account=" + c.sa("migrate"), "--command=python", "--args=/app/infrastructure/gcp/migrate.py",
            "--tasks=1", "--parallelism=1", "--max-retries=0", "--task-timeout=900s", "--cpu=1", "--memory=512Mi",
            "--set-cloudsql-instances=" + f"{c.project}:{c.region}:mindaam-postgres", "--set-env-vars=APP_ENV=" + env,
            "--set-secrets=" + f"DATABASE_URL=mindaam-{env}-migration-url:latest,RUNTIME_DATABASE_URL=mindaam-{env}-database-url:latest",
            "--labels=" + LABELS]
    c.gc(*args)
    c.gc("run", "jobs", "execute", name, "--region=" + c.region, "--wait")


def replace(c, manifest):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as f:
        json.dump(manifest, f); f.flush()
        c.gc("run", "services", "replace", f.name, "--region=" + c.region)


def optional_secrets(c, env):
    result = {}
    for key in OPTIONAL:
        name = f"mindaam-{env}-" + key.lower().replace("_", "-")
        if c.gc("secrets", "versions", "list", name, "--filter=state:ENABLED"):
            result[key] = name
    return result


def deploy(c, env, image, sha):
    c.require_project(); image_check(c, image)
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise Blocked("A full source commit SHA is required.")
    if not c.get_json("foundation.json"):
        raise Blocked("Run foundation first.")
    if env == "production":
        release_gate(c, image, sha)
    name = "mindaam-" + env
    previous = c.gc("run", "services", "describe", name, "--region=" + c.region, missing=True)
    if previous:
        c.owned(previous.get("metadata", {}), name)
        if c.get_json(f"releases/{sha}/{env}-previous.json") is None:
            c.put_json(f"releases/{sha}/{env}-previous.json", previous)
    migrate(c, env, image)
    origin = "https://" + SETTINGS["domain"] if env == "production" else (previous or {}).get("status", {}).get("url", "https://not-yet-published.invalid")
    manifest = service(c, env, image, origin, optional_secrets(c, env))
    replace(c, manifest)
    current = ready_service(c, name)
    provider_origin = current["status"]["url"]
    # First staging revision stays IAM-private until exact CSRF/cookie origin is known.
    if env == "staging" and origin != provider_origin:
        replace(c, service(c, env, image, provider_origin, optional_secrets(c, env)))
        origin = provider_origin
        current = ready_service(c, name)
    c.gc("run", "services", "add-iam-policy-binding", name, "--region=" + c.region,
         "--member=allUsers", "--role=roles/run.invoker", raw=True)
    if env == "production":
        vm_bundle(c, production_origin=provider_origin)
        foundation = c.get_json("foundation.json")
        summary(f"Production custom-domain DNS: A `mindaam.com` → `{foundation['media_ip']}`. No existing domain is overwritten automatically.")
    from release_policy import profile
    release = {"profile": profile(), "sha": sha, "image": image, "environment": env, "origin": origin, "provider_origin": provider_origin,
               "revision": current["status"]["latestReadyRevisionName"], "deployed_at": int(time.time())}
    c.put_json(f"releases/{sha}/{env}.json", release)
    Path("deployment-result.json").write_text(json.dumps(release, indent=2))
    summary(f"{env.title()} revision created: {provider_origin}. Deployment verification is still pending.")


def release_gate(c, image, sha):
    from release_policy import profile, evidence_name, review_name, required_checks, validate_beta, BETA
    selected = profile()
    verified = c.get_json(f"releases/{sha}/{evidence_name(selected)}")
    review = c.get_json(f"releases/{sha}/{review_name(selected)}")
    if selected == BETA:
        validate_beta(verified or {}, review or {})
        security = c.get_json(f"releases/{sha}/security-review.json")
        if not security or security != review.get("security_review") or security.get("sha") != sha or security.get("image") != image or security.get("evidence_object") != f"gs://{c.bucket}/releases/{sha}/security-review.json":
            raise Blocked("Security review must be a private exact-release evidence object")
    if not verified or verified.get("image") != image or verified.get("sha") != sha or time.time() - verified.get("verified_at", 0) > 7 * 86400:
        raise Blocked("Fresh staging acceptance for this exact image/source is required.")
    required = required_checks(selected) + ["performance"]
    if not all(verified.get("checks", {}).get(k) is True for k in required):
        raise Blocked("Staging acceptance is incomplete.")
    if not review or review.get("sha") != sha or review.get("image") != image or time.time() - review.get("reviewed_at", 0) > 7 * 86400:
        raise Blocked("Actual resource cost review is required for this release.")
    try:
        pricing_date = datetime.date.fromisoformat(review.get('pricing_date', ''))
    except (ValueError, TypeError):
        raise Blocked('Cost review requires an ISO pricing_date') from None
    if not 0 <= (datetime.date.today() - pricing_date).days <= 30:
        raise Blocked('Cost pricing must be dated within the last 30 days')
    inventory = review.get('inventory', {})
    if inventory.get('project') != c.project or not all(inventory.get(k) for k in ('sql', 'vm', 'staging', 'production_limits')):
        raise Blocked('Cost review requires actual project resource configuration')
    expected_metrics = f'gs://{c.bucket}/releases/{sha}/metrics.json'
    if review.get('resource_metrics_evidence') != expected_metrics:
        raise Blocked('Review must reference this exact release metrics object')
    components = ("cloud_run", "compute_livekit", "postgresql", "redis", "storage", "network", "logging", "other")
    def complete(value):
        if isinstance(value, dict): return bool(value) and all(complete(v) for v in value.values())
        if isinstance(value, list): return bool(value) and all(complete(v) for v in value)
        return value is not None and value != ''
    for scenario in ("idle", "light"):
        model = review.get("costs", {}).get(scenario, {})
        sources = model.get('pricing_sources')
        if (not complete(model.get("assumptions")) or not isinstance(sources, list) or not sources
                or any(not isinstance(source, str) or not source.startswith('https://') for source in sources)
                or set(model.get("usd", {})) != set(components)):
            raise Blocked("Cost model must itemize all resources, assumptions and pricing sources.")
        if any(not isinstance(n, (int, float)) or isinstance(n, bool) or not math.isfinite(n) or n < 0 for n in model["usd"].values()):
            raise Blocked("Invalid cost data")
    light = sum(review["costs"]["light"]["usd"].values())
    if light > SETTINGS["approval_above_usd"]:
        raise Blocked("Light-use estimate exceeds $150/month. Obtain explicit owner approval and a reviewed policy change.")
    if review.get("owner_approved") is not True or not all(isinstance(review.get(k), str) and review[k].startswith("gs://" + c.bucket + "/") for k in ("resource_metrics_evidence",)):
        raise Blocked("Actual resource metrics and cost review evidence are required.")


def rollback(c, sha):
    c.require_project()
    previous = c.get_json(f"releases/{sha}/production-previous.json")
    if not previous:
        raise Blocked("No previous production revision recorded for this release.")
    routed = [t["revisionName"] for t in previous["status"].get("traffic", []) if t.get("percent") == 100]
    if len(routed) != 1:
        raise Blocked("Previous traffic was split; review the recorded traffic map before rollback.")
    revision = routed[0]
    # Traffic-only rollback; databases, secrets and migrations are never rewound.
    c.gc("run", "services", "update-traffic", "mindaam-production", "--region=" + c.region, "--to-revisions=" + revision + "=100")
    summary("Production traffic restored to " + revision + ". Database compatibility must remain verified.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("operation", choices=["foundation", "staging", "production", "rollback"])
    p.add_argument("--project", required=True)
    p.add_argument("--image", default="")
    p.add_argument("--sha", default=os.getenv("GITHUB_SHA", ""))
    args = p.parse_args()
    try:
        cloud = Cloud(args.project)
        if args.operation == "foundation": foundation(cloud)
        elif args.operation == "rollback": rollback(cloud, args.sha)
        else: deploy(cloud, args.operation, args.image, args.sha)
    except Blocked as e:
        raise SystemExit(str(e))
