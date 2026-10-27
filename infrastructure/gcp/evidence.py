"""Persist real measurements and enforce staging evidence; no fabricated defaults."""
import argparse
import concurrent.futures
import datetime
import json
import math
import os
import statistics
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from readiness import ready_service
from common import Cloud, Blocked, command, HERE
REQUIRED_CHECKS = json.loads((HERE / "acceptance-checks.json").read_text())
from smoke import check


def metrics(c, release, *, timeout=600):
    token = command(["gcloud", "auth", "print-access-token"], sensitive=True)
    now = datetime.datetime.now(datetime.timezone.utc)
    end = now.isoformat(); start = (now - datetime.timedelta(minutes=30)).isoformat()
    types = ["custom.googleapis.com/mindaam/host_memory_utilization", "run.googleapis.com/container/cpu/utilizations", "run.googleapis.com/container/memory/utilizations",
             "run.googleapis.com/container/instance_count", "cloudsql.googleapis.com/database/cpu/utilization",
             "cloudsql.googleapis.com/database/memory/utilization", "cloudsql.googleapis.com/database/postgresql/num_backends",
             "compute.googleapis.com/instance/cpu/utilization", "compute.googleapis.com/instance/network/sent_bytes_count"]
    vm = c.gc('compute', 'instances', 'describe', 'mindaam-media', '--zone=' + c.zone)
    c.owned(vm, 'media VM')
    result = {}; deadline = time.monotonic() + timeout
    while True:
      for metric in types:
        if metric.startswith('run.'):
            scope = f'resource.type = "cloud_run_revision" AND resource.labels.service_name = "mindaam-staging" AND resource.labels.revision_name = "{release["revision"]}"'
        elif metric.startswith('cloudsql.'):
            scope = f'resource.type = "cloudsql_database" AND resource.labels.database_id = "{c.project}:mindaam-postgres"'
        elif metric.startswith('compute.'):
            scope = f'resource.type = "gce_instance" AND resource.labels.instance_id = "{vm["id"]}"'
        else:
            scope = f'resource.type = "global" AND resource.labels.project_id = "{c.project}"'
        if result.get(metric, {}).get('timeSeries') and any(t.get('points') for t in result[metric]['timeSeries']):
            continue
        params = {"filter": f'metric.type = "{metric}" AND {scope}', "interval.startTime": start,
                  "interval.endTime": datetime.datetime.now(datetime.timezone.utc).isoformat(), "view": "FULL", "pageSize": 1000}
        series = []
        while True:
            request = Request(f"https://monitoring.googleapis.com/v3/projects/{c.project}/timeSeries?{urlencode(params)}", headers={"Authorization": "Bearer " + token})
            try:
                with urlopen(request, timeout=15) as r:
                    response = json.load(r)
            except HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504):
                    raise Blocked(f'Monitoring {metric}: HTTP {error.code}; inspect metric type/permissions') from None
                response = {}; break
            except (URLError, TimeoutError):
                response = {}; break
            series.extend(response.get('timeSeries', []))
            if not response.get('nextPageToken'):
                break
            if time.monotonic() >= deadline:
                raise Blocked('Monitoring pagination exceeded deadline: ' + metric)
            params['pageToken'] = response['nextPageToken']
        result[metric] = {'timeSeries': series}
      missing = [m for m in types if not any(t.get('points') for t in result.get(m, {}).get('timeSeries', []))]
      if not missing:
          return {"interval_start": start, "interval_end": datetime.datetime.now(datetime.timezone.utc).isoformat(), "series": result}
      if time.monotonic() >= deadline:
          raise Blocked('Monitoring ingestion deadline; missing: ' + ', '.join(missing)
                        + '. For host memory inspect mindaam-reconcile.service and metricWriter delivery.')
      time.sleep(min(20, max(0, deadline - time.monotonic())))


def bounded_http(origin):
    # This is a short HTTP saturation check, NOT a 25-player/media capacity claim.
    result = []
    for concurrency in (2, 10, 25):
        def request(_):
            before = time.monotonic()
            with urlopen(origin + "/api/health", timeout=30) as r:
                assert json.load(r)["status"] == "ready"
            return (time.monotonic() - before) * 1000
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            samples = sorted(pool.map(request, range(concurrency * 2)))
        p95 = samples[min(len(samples) - 1, int(len(samples) * .95))]
        result.append({"concurrent_requests": concurrency, "samples": len(samples), "p50_ms": statistics.median(samples), "p95_ms": p95})
        if p95 > 5000:
            raise Blocked("HTTP p95 exceeded 5 seconds; stop and investigate before increasing load.")
    return result


def verify(c, sha):
    release = c.get_json(f"releases/{sha}/staging.json")
    if not release:
        raise Blocked("No staging deployment for this commit")
    current = ready_service(c, "mindaam-staging")
    if current["spec"]["template"]["spec"]["containers"][0]["image"] != release["image"] or current["status"]["latestReadyRevisionName"] != release["revision"]:
        raise Blocked("Staging service has moved to a different image/revision; do not attest an older release")
    smoke = check(release)
    browser = json.loads(Path("gcp-evidence/browser.json").read_text())
    if browser.get("origin") != release["origin"] or browser.get("sha") != sha:
        raise Blocked("Browser evidence does not match this release")
    required = REQUIRED_CHECKS
    for filename, forced in [('direct.json', False), ('relay.json', True)]:
        attempt = json.loads(Path('gcp-evidence', filename).read_text())
        expected = [key for key in required if forced or key != 'turn_tls']
        if (attempt.get('sha') != sha or attempt.get('origin') != release['origin']
                or attempt.get('forced_turn') is not forced
                or not all(attempt.get('checks', {}).get(k) is True for k in expected)):
            raise Blocked('Direct/relay acceptance is incomplete or mismatched: ' + filename)
    if not all(browser.get("checks", {}).get(k) is True for k in required):
        raise Blocked("Real browser/media acceptance is incomplete")
    http = bounded_http(release["origin"])
    measured = metrics(c, release)
    c.put_json(f"releases/{sha}/metrics.json", measured)
    if any(not result.get("timeSeries") for result in measured["series"].values()):
        raise Blocked("Cloud Monitoring data has not arrived for every required metric; resume verify after ingestion.")
    utilization = {}
    for metric, response in measured["series"].items():
        if not any(word in metric for word in ("cpu/", "memory/", "memory_utilization")):
            continue
        samples = []
        for series in response["timeSeries"]:
            for point in series.get("points", [])[:5]:
                value = point.get("value", {})
                sample = value.get("doubleValue", value.get("distributionValue", {}).get("mean"))
                if sample is not None:
                    sample = float(sample)
                    if not math.isfinite(sample) or sample < 0:
                        raise Blocked('Invalid utilization sample: ' + metric)
                    samples.append(sample)
        if not samples:
            raise Blocked("Required utilization samples are missing: " + metric)
        utilization[metric] = statistics.median(samples)
        if utilization[metric] > .90:
            raise Blocked("Measured resource saturation exceeds 90%; investigate before production: " + metric)
    evidence = {**release, "verified_at": int(time.time()), "checks": {**browser["checks"], "performance": True},
                "smoke": smoke, "http": http, "browser": browser, "median_utilization": utilization,
                "resource_metrics_evidence": f"gs://{c.bucket}/releases/{sha}/metrics.json",
                "limitations": "Three synthetic-capture browsers and bounded HTTP requests. Not physical-device or 500/1000 CCU certification."}
    c.put_json(f"releases/{sha}/staging-verified.json", evidence)
    Path("gcp-evidence/staging-verified.json").write_text(json.dumps(evidence, indent=2))
    print("Real GCP staging acceptance recorded: " + release["origin"])


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--project", required=True); p.add_argument("--sha", default=os.getenv("GITHUB_SHA"))
    args = p.parse_args(); c = Cloud(args.project); c.require_project()
    verify(c, args.sha)
