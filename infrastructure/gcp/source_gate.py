"""Reuse successful application CI only when all application/test bytes are identical."""
import json
import subprocess
import sys
from common import Blocked, SETTINGS, command


def application_path(path):
    return not (path.startswith("infrastructure/gcp/") or path.startswith(".github/workflows/gcp-")
                or path in {"docs/STATUS.md", "docs/ARCHITECTURE.md", "STATUS.md", "ARCHITECTURE.md", "docs/ADR-0022-gcp-automation.md"})


def main():
    head = command(["git", "rev-parse", "HEAD"])
    # Explicit successful baseline or newer successful run; never infer pass from a skipped job.
    for page in range(1, 6):
        runs = json.loads(command(["gh", "api", f"repos/{SETTINGS['repository']}/actions/workflows/ci.yml/runs?status=success&event=push&per_page=100&page={page}"]))["workflow_runs"]
        for run in runs:
            base = run["head_sha"]
            ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", base, head], capture_output=True)
            if ancestor.returncode:
                continue
            changed = command(["git", "diff", "--name-only", base, head]).splitlines()
            # The initial paths-ignore change only changes triggers. All actual job definitions must match.
            if ".github/workflows/ci.yml" in changed:
                old = command(["git", "show", base + ":.github/workflows/ci.yml"])
                new = command(["git", "show", head + ":.github/workflows/ci.yml"])
                if old.split("\njobs:\n", 1)[1] != new.split("\njobs:\n", 1)[1]:
                    continue
                changed.remove(".github/workflows/ci.yml")
            if any(application_path(p) for p in changed):
                continue
            jobs = []
            for jobpage in range(1, 5):
                batch = json.loads(command(["gh", "api", f"repos/{SETTINGS['repository']}/actions/runs/{run['id']}/jobs?filter=latest&per_page=100&page={jobpage}"]))["jobs"]
                jobs.extend(batch)
                if len(batch) < 100:
                    break
            if len(jobs) < 16 or any(j.get("conclusion") != "success" for j in jobs):
                continue
            print("Application CI reused with identical application/test content: " + run["html_url"])
            return
        if len(runs) < 100:
            break
    raise Blocked("No fully successful application CI run with identical source/tests. Let the existing Validation workflow finish first.")


if __name__ == "__main__":
    try:
        main()
    except Blocked as e:
        sys.exit(str(e))
