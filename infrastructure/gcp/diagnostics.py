"""Read-only database pressure and public price evidence. Never grants release approval."""
import datetime
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from common import command


def get_json(url, token, project):
    request = Request(url, headers={"Authorization": "Bearer " + token, "x-goog-user-project": project})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def collect(c):
    token = command(["gcloud", "auth", "print-access-token"], sensitive=True)
    now = datetime.datetime.now(datetime.timezone.utc)
    start = (now - datetime.timedelta(hours=24)).isoformat()
    result = {"collected_at": now.isoformat(), "interval_start": start, "read_only": True,
              "release_approval": False, "memory_gate_threshold": .90, "metrics": {}, "errors": {}}
    names = ["memory/components", "memory/quota", "memory/usage", "memory/total_usage", "memory/utilization",
             "cpu/utilization", "postgresql/num_backends", "postgresql/transaction_count"]
    for name in names:
        metric = "cloudsql.googleapis.com/database/" + name
        params = {"filter": f'metric.type = "{metric}" AND resource.type = "cloudsql_database" AND resource.labels.database_id = "{c.project}:mindaam-postgres"',
                  "interval.startTime": start, "interval.endTime": now.isoformat(), "view": "FULL", "pageSize": 1000}
        series = []
        try:
            for _ in range(20):
                page = get_json("https://monitoring.googleapis.com/v3/projects/" + c.project + "/timeSeries?" + urlencode(params), token, c.project)
                series.extend(page.get("timeSeries", []))
                if not page.get("nextPageToken"): break
                params["pageToken"] = page["nextPageToken"]
            else: raise ValueError("pagination incomplete")
            result["metrics"][name] = series
        except (HTTPError, OSError, ValueError) as error:
            result["errors"][name] = "HTTP " + str(error.code) if isinstance(error, HTTPError) else type(error).__name__
    # Return only timestamps/severity, never SQL text, account data or connection strings.
    try:
        query = f'resource.type="cloudsql_database" AND resource.labels.database_id="{c.project}:mindaam-postgres" AND timestamp>="{start}" AND ("out of memory" OR "Out of Memory" OR "signal 9" OR "excessive memory usage")'
        rows = c.gc("logging", "read", query, "--limit=100", "--format=json(timestamp,severity)")
        result["memory_error_logs"] = rows
        result["memory_error_logs_limit"] = 100
    except Exception:
        result["errors"]["memory_error_logs"] = "Read unavailable; not verified"
    result["public_prices"] = prices(c, token)
    return result


def prices(c, token):
    root = "https://cloudbilling.googleapis.com/v1/"
    result = {"currency": "USD", "region": c.region, "account_discounts_verified": False, "skus": [], "errors": {}}
    selected = {"Cloud SQL", "Compute Engine", "Cloud Run", "Cloud Storage", "Secret Manager", "Cloud Logging", "Artifact Registry"}
    try:
        services = get_json(root + "services?pageSize=5000", token, c.project)
        if services.get("nextPageToken"): raise ValueError("service list incomplete")
        for service in services.get("services", []):
            if service["displayName"] not in selected: continue
            params = {"currencyCode": "USD", "pageSize": 5000}
            for _ in range(30):
                page = get_json(root + service["name"] + "/skus?" + urlencode(params), token, c.project)
                for sku in page.get("skus", []):
                    if not set(sku.get("serviceRegions", [])) & {c.region, "global", "europe"}: continue
                    if sku.get("category", {}).get("usageType") != "OnDemand": continue
                    if service["displayName"] == "Compute Engine" and not re.search(r"E2|Storage|IP|Internet|Network", sku.get("description", ""), re.I): continue
                    result["skus"].append({k:sku.get(k) for k in ("skuId", "description", "category", "serviceRegions", "pricingInfo")})
                if not page.get("nextPageToken"): break
                params["pageToken"] = page["nextPageToken"]
            else: result["errors"][service["displayName"]] = "SKU pagination incomplete"
    except (HTTPError, OSError, ValueError) as error:
        result["errors"]["catalog"] = "HTTP " + str(error.code) if isinstance(error, HTTPError) else type(error).__name__
    return result
