"""Run ONCE as the account owner in Cloud Shell; safe to resume after interruption.

Creates authentication/permissions only. No VM or SQL instance is purchased here.
The owner reviews/runs this committed script; no service-account key is generated.
"""
import argparse
import json
from common import Cloud, Blocked, SETTINGS, command, summary

APIS = ["serviceusage.googleapis.com", "iam.googleapis.com", "iamcredentials.googleapis.com",
        "sts.googleapis.com", "cloudresourcemanager.googleapis.com", "compute.googleapis.com",
        "run.googleapis.com", "sqladmin.googleapis.com", "artifactregistry.googleapis.com",
        "secretmanager.googleapis.com", "storage.googleapis.com", "monitoring.googleapis.com",
        "logging.googleapis.com", "billingbudgets.googleapis.com", "cloudbilling.googleapis.com"]
DEPLOY_ROLES = ["roles/run.admin", "roles/compute.instanceAdmin.v1", "roles/compute.networkAdmin",
                "roles/compute.securityAdmin", "roles/cloudsql.admin", "roles/artifactregistry.admin",
                "roles/secretmanager.admin", "roles/storage.admin", "roles/monitoring.viewer",
                "roles/logging.viewer", "roles/serviceusage.serviceUsageConsumer", "roles/browser"]


def bootstrap(c, budget_amount="125USD"):
    account = json.loads(command(["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=json"]))
    if [x["account"] for x in account] != [SETTINGS["owner_email"]]:
        raise Blocked("Choose sain@scalivora.com in Cloud Shell before continuing.")
    repo = json.loads(command(["gh", "api", "repos/" + SETTINGS["repository"]]))
    if str(repo["id"]) != SETTINGS["repository_id"] or str(repo["owner"]["id"]) != SETTINGS["owner_id"] or not repo["private"]:
        raise Blocked("GitHub identity/repository does not match the private Mindaam repository.")
    billing = c.require_project(bootstrap=True)
    c.gc("projects", "update", c.project, "--update-labels=application=mindaam")
    c.gc("services", "enable", *APIS)
    identities = ["deploy", "staging", "production", "migrate", "media"]
    for name in identities:
        if c.gc("iam", "service-accounts", "describe", c.sa(name), missing=True) is None:
            c.gc("iam", "service-accounts", "create", "mindaam-" + name, "--display-name=Mindaam " + name)
    for role in DEPLOY_ROLES:
        c.gc("projects", "add-iam-policy-binding", c.project, "--member=serviceAccount:" + c.sa("deploy"), "--role=" + role, "--condition=None", raw=True)
    # No Owner, Editor, project-IAM-admin or service-account-key-admin granted to CI.
    for name in identities[1:]:
        c.gc("iam", "service-accounts", "add-iam-policy-binding", c.sa(name), "--member=serviceAccount:" + c.sa("deploy"), "--role=roles/iam.serviceAccountUser", raw=True)
    for name in ("staging", "production", "migrate"):
        c.gc("projects", "add-iam-policy-binding", c.project, "--member=serviceAccount:" + c.sa(name), "--role=roles/cloudsql.client", "--condition=None", raw=True)
    for role in ("roles/logging.logWriter", "roles/monitoring.metricWriter"):
        c.gc("projects", "add-iam-policy-binding", c.project, "--member=serviceAccount:" + c.sa("media"), "--role=" + role, "--condition=None", raw=True)
    pool = "mindaam-github"
    if c.gc("iam", "workload-identity-pools", "describe", pool, "--location=global", missing=True) is None:
        c.gc("iam", "workload-identity-pools", "create", pool, "--location=global", "--display-name=Mindaam GitHub")
    mapping = "google.subject=assertion.sub," + ",".join(f"attribute.{x}=assertion.{x}" for x in ["repository_id", "repository_owner_id", "ref", "workflow_ref", "event_name"])
    condition = (f"assertion.repository_id == '{SETTINGS['repository_id']}' && "
                 f"assertion.repository_owner_id == '{SETTINGS['owner_id']}' && "
                 "assertion.ref == 'refs/heads/main' && assertion.event_name == 'workflow_dispatch' && "
                 f"assertion.workflow_ref == '{SETTINGS['repository']}/.github/workflows/gcp-deploy.yml@refs/heads/main'")
    exists = c.gc("iam", "workload-identity-pools", "providers", "describe", "github", "--workload-identity-pool=" + pool, "--location=global", missing=True)
    c.gc("iam", "workload-identity-pools", "providers", "update-oidc" if exists else "create-oidc", "github",
         "--workload-identity-pool=" + pool, "--location=global", "--issuer-uri=https://token.actions.githubusercontent.com",
         "--attribute-mapping=" + mapping, "--attribute-condition=" + condition)
    provider = f"projects/{c.number}/locations/global/workloadIdentityPools/{pool}/providers/github"
    member = f"principalSet://iam.googleapis.com/projects/{c.number}/locations/global/workloadIdentityPools/{pool}/attribute.repository_id/{SETTINGS['repository_id']}"
    c.gc("iam", "service-accounts", "add-iam-policy-binding", c.sa("deploy"), "--member=" + member, "--role=roles/iam.workloadIdentityUser", raw=True)
    command(["gh", "variable", "set", "MINDAAM_BUDGET_CONFIRMED", "--repo", SETTINGS["repository"], "--body", "false"])
    for key, value in {"MINDAAM_PROJECT_ID": c.project, "MINDAAM_WIF_PROVIDER": provider, "MINDAAM_DEPLOY_SA": c.sa("deploy")}.items():
        command(["gh", "variable", "set", key, "--repo", SETTINGS["repository"], "--body", value])
    # Project-scoped alerts, not a hard spending cap. Currency must match billing.
    account_id = billing["billingAccountName"].split("/")[-1]
    # Budget API validates the billing-account currency. Never silently skip alerts.
    # For a non-USD account the owner supplies the reviewed local equivalent on resume.
    import re
    if not re.fullmatch(r"[1-9][0-9]*(?:\.[0-9]{1,2})?[A-Z]{3}", budget_amount):
        raise Blocked("Invalid local-currency budget amount")
    if budget_amount.endswith("USD") and float(budget_amount[:-3]) > SETTINGS["budget_usd"]:
        raise Blocked("The startup budget warning cannot exceed $125 USD.")
    budgets = c.gc("billing", "budgets", "list", "--billing-account=" + account_id)
    existing = next((b for b in budgets if b.get("displayName") == "Mindaam startup " + c.project), None)
    if existing:
        if existing.get("budgetFilter", {}).get("projects") != ["projects/" + c.number]:
            raise Blocked("Existing budget is not scoped exclusively to Mindaam")
        c.gc("billing", "budgets", "update", existing["name"].split("/")[-1],
             "--billing-account=" + account_id, "--budget-amount=" + budget_amount,
             "--credit-types-treatment=exclude-all-credits")
    else:
        c.gc("billing", "budgets", "create", "--billing-account=" + account_id,
             "--display-name=Mindaam startup " + c.project, "--budget-amount=" + budget_amount,
             "--filter-projects=projects/" + c.number, "--credit-types-treatment=exclude-all-credits",
             *["--threshold-rule=percent=" + v for v in ("0.4", "0.6", "0.8", "1.0")])
    command(["gh", "variable", "set", "MINDAAM_BUDGET_CONFIRMED", "--repo", SETTINGS["repository"], "--body", "true"])
    summary("Keyless authentication configured for scalivoraai-hash/Mindaam, main, and the manual GCP deployment workflow only. Return to the existing conversation to continue; do not send any credentials.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--budget-amount", default="125USD")
    args = p.parse_args()
    try:
        bootstrap(Cloud(args.project), args.budget_amount)
    except Blocked as e:
        raise SystemExit(str(e))
