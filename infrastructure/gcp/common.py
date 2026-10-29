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
        # Cloud Run emits a name-only diagnostic. Bind it to the exact requested
        # managed resource; malformed names and other commands are not absence.
        run_missing = False
        if (len(args) >= 5 and args[:2] == ['gcloud', 'run']
                and args[2] in ('services', 'jobs') and args[3] == 'describe'):
            kind = 'service' if args[2] == 'services' else 'job'
            pattern = r'mindaam-(?:staging|production)' if kind == 'service' else r'mindaam-migrate-(?:staging|production)'
            if re.fullmatch(pattern, args[4]):
                run_missing = re.search(
                    r'^ERROR: \(gcloud\.run\.' + args[2] + r'\.describe\) Cannot find '
                    + kind + r' \[' + re.escape(args[4]) + r'\]\.?[ \t]*$',
                    message, re.MULTILINE) is not None
        # Artifact Registry's name-only diagnostic is valid only for this lookup.
        # Full-message matching prevents unrelated repository/project errors from
        # being swallowed alongside an apparent missing-image line.
        image_lookup = (len(args) >= 6
                        and args[:5] == ['gcloud', 'artifacts', 'docker', 'images', 'describe'])
        image_lines = [line.rstrip() for line in message.splitlines() if line.strip()]
        image_missing_forms = [
            ['ERROR: (gcloud.artifacts.docker.images.describe) Image not found.'],
            [
                'ERROR: (gcloud.artifacts.docker.images.describe) Image not found.',
                'A valid container image can be referenced by tag or digest, has the format of',
                '  LOCATION-docker.pkg.dev/PROJECT-ID/REPOSITORY-ID/IMAGE:tag',
                '  LOCATION-docker.pkg.dev/PROJECT-ID/REPOSITORY-ID/IMAGE@sha256:digest',
            ],
        ]
        image_missing = image_lookup and image_lines in image_missing_forms
        # An authentication/network/permission error must NEVER become 'not found'.
        missing = (image_missing or run_missing or any(t in message for t in ("NOT_FOUND", "was not found", "does not exist", "No URLs matched"))
                   or re.search(r"\bnot found: 404\b", message) is not None
                   # Match the Storage diagnostic header, not text inside an object URL.
                   or re.search(r"^ERROR: \(gcloud\.storage\.cat\) "
                                r"The following URLs matched no objects or files:[ \t]*$",
                                message, re.MULTILINE) is not None
                   # Cloud SQL uses HTTPError; require both the status and reason.
                   # A bare 404 or an arbitrary HTTP error is not missing evidence.
                   or re.search(r"\bHTTP(?:Error)?[ \t]+404:[ \t]+Not Found(?=[.\s]|$)",
                                message, re.IGNORECASE) is not None)
        # Match failure statuses/phrases, not nouns in CLI context such as
        # "using the credentials" or resource paths such as "compute.networks".
        # Inspect the entire message so identity context cannot hide a later error.
        failure = re.search(
            r"\b(?:permission_denied|unauthenticated|unauthorized|forbidden|401|403|"
            r"deadline_exceeded|unavailable|timeout|timed out|resource_exhausted|"
            r"quota_exceeded|invalid_argument|failed_precondition|bad_request)\b"
            r"|\bHTTP(?:Error)?[ \t]+(?:(?!404\b)[45]\d{2})\b"
            r"|\b(?:quota|rate limit|malformed request|bad request|invalid argument|invalid request|"
            r"(?:invalid|malformed) (?:path|url|uri|resource|service|job|project|region)|"
            r"(?:wrong|unknown) (?:project|region))\b"
            r"|\b(?:project|region)[ \t]+[^\n]{0,100}?"
            r"\b(?:not found|does not exist|is invalid)\b"
            r"|permission(?:s)?[ _]+(?:denied|missing|required)"
            r"|(?:access denied|reauth|could not refresh|invalid_grant)"
            r"|(?:credential\w*|authentication|authorization|network|connection|dns|"
            r"name resolution|ssl|tls|proxy|transport)[^\n.]{0,100}"
            r"\b(?:fail\w*|error\w*|invalid|expired|revoked|denied|refused|reset|"
            r"unreachable|required|unavailable|timed out)\b"
            r"|\b(?:invalid|expired|revoked|missing|failed|unable|cannot|could not|no valid)"
            r"[^\n.]{0,100}(?:credential\w*|authenticat\w*|authoriz\w*|"
            r"connect\w*|resolv\w*|network|dns|ssl|tls|proxy|transport)",
            message, re.IGNORECASE,
        ) is not None
        if image_lookup and re.search(
                r'\b(?:invalid|unknown|wrong|malformed) repository\b'
                r'|\brepository\b[^\n]{0,100}\b(?:not found|does not exist|invalid|denied|unavailable)\b',
                message, re.IGNORECASE):
            failure = True
        if allow_missing and missing and not failure:
            return None
        detail = "Sensitive command failed; consult the provider audit log." if sensitive else message[-1800:]
        raise Blocked(detail)
    return result.stdout.strip()


class Cloud:
    def __init__(self, project):
        if project != "mindaam" and not re.fullmatch(r"mindaam-[a-z0-9-]{1,21}[a-z0-9]", project):
            raise Blocked("Use the dedicated mindaam or mindaam-* project ID, never an unrelated project.")
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
            allowed_names = {"Mindaam Production"}
            if self.project == "mindaam":
                allowed_names.add("Mindaam")
            if project.get("name") not in allowed_names:
                raise Blocked("The selected project must be named Mindaam Production (or Mindaam for project mindaam).")
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

