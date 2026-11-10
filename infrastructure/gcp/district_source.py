"""Bind district acceptance to an unchanged application and explicit harness commit."""
import re
from common import Blocked, command
from source_gate import application_path


def verify_source(release_sha, harness_sha):
    if not all(re.fullmatch(r"[0-9a-f]{40}", value or "") for value in (release_sha, harness_sha)):
        raise Blocked("Invalid district release or harness SHA")
    command(["git", "merge-base", "--is-ancestor", release_sha, harness_sha])
    changed = command(["git", "diff", "--name-only", release_sha, harness_sha]).splitlines()
    if any(application_path(path) for path in changed):
        raise Blocked("Application or application-test drift since deployed staging image")
    return {"application_sha": release_sha, "harness_sha": harness_sha}
