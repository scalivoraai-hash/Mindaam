"""Small, explicit gcloud adapter. No default project, shell interpolation or secret logs."""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SETTINGS = json.loads((HERE / "settings.json").read_text())
LABELS = "application=mindaam,managed_by=mindaam-github"


class Blocked(RuntimeError):
    pass


def command(args, *, stdin=None, sensitive=False, allow_missing=False):
    result = subprocess.run(args, input=stdin, text=True, capture_output=True)
    if result.returncode:
        message = result.stderr
        # An authentication/network/permission error must NEVER become 'not found'.
        if allow_missing and any(t in message for t in ("NOT_FOUND", "was not found", "does not exist", "No URLs matched")) and not any(t in message for t in ("PERMISSION_DENIED", "403", "UNAUTHENTICATED", "Permission", "permission", "401")):
            return None
        detail = "Sensitive command failed; consult the provider audit log." if sensitive else message[-1800:]
        raise Blocked(detail)
    return result.stdout.strip()


class Cloud:
    def __init__(self, project):
        if not re.fullmatch(r"mindaam-[a-z0-9-]{1,21}[a-z0-9]", project):
            raise Blocked("Use the dedicated mindaam-* project ID, never an unrelated project.")
        self.project = project
        self.region = SETTINGS["region"]
        self.zone = SETTINGS["zone"]
        self.bucket = project + "-releases"
        self.assets = project + "-assets"

    def gc(self, *args, missing=False, sensitive=False, stdin=None, raw=False):
        output = command(["gcloud", *args, "--project=" + self.project, "--quiet", "--format=json" if not raw else "--format=none"], stdin=stdin, sensitive=sensitive, allow_missing=missing)
        return output if raw or output is None else json.loads(output or "null")

    def file_command(self, args, payload, *, sensitive=False):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as f:
            os.chmod(f.name, 0o600)
            json.dump(payload, f)
            f.flush()
            return self.gc(*args, "--flags-file=" + f.name, sensitive=sensitive)

    def require_project(self, *, bootstrap=False):
        project = self.gc("projects", "describe", self.project)
        if project.get("lifecycleState") != "ACTIVE":
            raise Blocked("Dedicated project is not active.")
        if bootstrap:
            if project.get("name") != "Mindaam Production":
                raise Blocked("The selected project must be named Mindaam Production.")
        elif project.get("labels", {}).get("application") != "mindaam":
            raise Blocked("Project has not completed the Mindaam bootstrap.")
        billing = self.gc("billing", "projects", "describe", self.project)
        if not billing.get("billingEnabled"):
            raise Blocked("Link the intended billing account to this project first.")
        self.number = str(project["projectNumber"])
        return billing

    def sa(self, name):
        return f"mindaam-{name}@{self.project}.iam.gserviceaccount.com"

    def owned(self, resource, name):
        labels = resource.get("labels", resource.get("settings", {}).get("userLabels", {}))
        if labels.get("application") != "mindaam":
            raise Blocked(f"Refusing to adopt unlabelled resource {name}.")
        return resource

    def secret(self, name, *, generate=None, readers=()):
        current = self.gc("secrets", "describe", name, missing=True)
        if current is None:
            self.gc("secrets", "create", name, "--replication-policy=automatic", "--labels=" + LABELS)
        else:
            self.owned(current, name)
        versions = self.gc("secrets", "versions", "list", name, "--filter=state:ENABLED")
        if not versions:
            if generate is None:
                raise Blocked(f"Secret {name} needs its value entered directly in Secret Manager.")
            self.gc("secrets", "versions", "add", name, "--data-file=-", stdin=generate(), sensitive=True)
        for reader in readers:
            self.gc("secrets", "add-iam-policy-binding", name, "--member=serviceAccount:" + reader, "--role=roles/secretmanager.secretAccessor", raw=True)
        return name

    def secret_value(self, name):
        # 'access' returns bytes, not JSON. Never pass through logging/artifacts.
        return command(["gcloud", "secrets", "versions", "access", "latest", "--secret=" + name, "--project=" + self.project], sensitive=True)

    def put_json(self, key, value):
        with tempfile.NamedTemporaryFile(mode="w") as f:
            json.dump(value, f)
            f.flush()
            self.gc("storage", "cp", f.name, f"gs://{self.bucket}/{key}", raw=True)

    def get_json(self, key):
        data = command(["gcloud", "storage", "cat", f"gs://{self.bucket}/{key}", "--project=" + self.project], allow_missing=True)
        return None if data is None else json.loads(data)


def summary(message):
    print(message)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(message + "\n\n")
