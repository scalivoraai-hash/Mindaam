"""Dispatch immutable, resumable releases; all subprocess inputs are separate argv."""
import json
import os
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path
from common import Cloud, Blocked, SETTINGS, command, summary
from deploy import foundation, deploy, rollback, image_check
from smoke import check
from readiness import ready_service
from finalize import finalize


def staging_image(c, sha, *, build_allowed, build_ref=None):
    existing = c.get_json(f'releases/{sha}/staging.json')
    if existing is not None:
        if existing.get('sha') != sha or existing.get('environment') != 'staging':
            raise Blocked('Existing staging state does not match the requested release')
        image = existing.get('image', '')
    else:
        registry = c.region + '-docker.pkg.dev'
        tag = f'{registry}/{c.project}/mindaam/app:{sha}'
        info = c.gc('artifacts', 'docker', 'images', 'describe', tag, missing=True)
        if info is None:
            if not build_allowed:
                raise Blocked('Ancestor staging image is absent; never build current code under an old SHA')
            c.gc('auth', 'configure-docker', registry, raw=True)
            if build_ref is None:
                subprocess.run(['docker', 'build', '-f', 'infrastructure/gcp/Dockerfile', '-t', tag, '.'], check=True)
            else:
                if build_ref != sha or not re.fullmatch(r'[a-f0-9]{40}', build_ref):
                    raise Blocked('Build source must match the requested full release SHA')
                # Build exact tracked release bytes, never current HEAD under an old tag.
                with tempfile.TemporaryDirectory() as directory:
                    archive = Path(directory) / 'source.tar'
                    context = Path(directory) / 'source'
                    context.mkdir()
                    subprocess.run(['git', 'archive', '--format=tar', '--output=' + str(archive), build_ref], check=True)
                    with tarfile.open(archive) as source:
                        source.extractall(context, filter='data')
                    subprocess.run(['docker', 'build', '-f', str(context / 'infrastructure/gcp/Dockerfile'),
                                    '-t', tag, str(context)], check=True)
            subprocess.run(['docker', 'push', tag], check=True)
            info = c.gc('artifacts', 'docker', 'images', 'describe', tag)
        digest = (info or {}).get('image_summary', {}).get('digest', '')
        image = tag.rsplit(':', 1)[0] + '@' + digest
    image_check(c, image)
    return image


def main():
    from release_policy import profile, BETA, POLICY, evidence_name, review_name
    selected = profile()
    operation = os.environ['OPERATION']
    c = Cloud(os.environ['MINDAAM_PROJECT_ID']); c.require_project()
    sha = os.environ['RELEASE_SHA']
    if not re.fullmatch(r'[a-f0-9]{40}', sha):
        raise Blocked('A complete release SHA is required')
    # Old release references are allowed only if still present in this repository's main history.
    if subprocess.run(['git', 'merge-base', '--is-ancestor', sha, 'HEAD'], capture_output=True).returncode:
        raise Blocked('Release is not in Mindaam main history')
    if selected == BETA and subprocess.run(['git','merge-base','--is-ancestor',POLICY['base_sha'],sha],capture_output=True).returncode:
        raise Blocked('Beta policy is limited to descendants of the reviewed Mindaam release')
    if operation == 'review':
        from review import packet
        Path('gcp-evidence').mkdir(exist_ok=True)
        value = packet(c, sha)
        from diagnostics import collect
        value["database_diagnostics"] = collect(c)
        c.put_json(f'releases/{sha}/review-draft.json', value)
        Path('gcp-evidence/review-draft.json').write_text(json.dumps(value, indent=2))
        return
    if operation == 'foundation':
        foundation(c); return
    if operation == 'finalize':
        finalize(c, sha); return
    if operation == 'rollback':
        rollback(c, sha); return
    if operation == 'staging':
        head = command(['git', 'rev-parse', 'HEAD'])
        if sha != head:
            # Resume an ancestor image only across reviewed orchestration changes.
            # Runtime code, Dockerfile, migration script and build inputs must match.
            changed = command(['git', 'diff', '--name-only', sha, head]).splitlines()
            allowed = {'infrastructure/gcp/common.py', 'infrastructure/gcp/deploy.py',
                       'infrastructure/gcp/workflow.py', 'docs/ADR-0022-gcp-automation.md'}
            if any(p not in allowed and not p.startswith('infrastructure/gcp/tests/') for p in changed):
                raise Blocked('Staging resume requires unchanged application and image build inputs')
        if not c.get_json('foundation.json'):
            raise Blocked('Complete foundation and media/turn DNS first')
        image = staging_image(c, sha, build_allowed=True, build_ref=sha if sha != head else None)
        deploy(c, 'staging', image, sha)
    elif operation in ('verify', 'verify-resources'):
        release = c.get_json(f'releases/{sha}/staging.json')
        if not release:
            raise Blocked('No existing staging release for this SHA')
        if release.get('profile','full') != selected:
            raise Blocked('Requested profile does not match the staged runtime; deploy the gated source first')
        current = ready_service(c, "mindaam-staging")
        if (current["status"]["latestReadyRevisionName"] != release["revision"]
                or current["spec"]["template"]["spec"]["containers"][0]["image"] != release["image"]):
            raise Blocked("Requested staging revision is no longer current")
        Path('deployment-result.json').write_text(json.dumps(release, indent=2))
    elif operation == 'production':
        staged = c.get_json(f'releases/{sha}/{evidence_name()}')
        if not staged:
            raise Blocked('Actual staging acceptance is required')
        object_name = os.getenv('REVIEW_OBJECT', '')
        expected = f'releases/{sha}/{review_name()}'
        if object_name != expected:
            raise Blocked('Select the exact private release review prepared for this SHA: ' + expected)
        deploy(c, 'production', staged['image'], sha)
    else:
        raise Blocked('Unknown operation')
    release = json.loads(Path('deployment-result.json').read_text())
    # Production provider readiness precedes owner-controlled DNS cutover.
    result = check({**release, 'origin': release['provider_origin']} if operation == 'production' else release)
    Path('smoke-result.json').write_text(json.dumps(result, indent=2))
    if operation == 'production':
        c.put_json(f'releases/{sha}/production-provider-verified.json', {**release, 'smoke': result})
        inventory = c.get_json('foundation.json')
        summary('Production provider ready; apex is NOT yet verified. In GoDaddy set A @ to '
                + inventory['media_ip'] + ' (remove conflicting @ A/AAAA or forwarding). '
                + 'Leave media and turn records unchanged. www is not configured; do not point it here. '
                + 'After propagation dispatch finalize for the same release SHA. Do not rerun production just to verify DNS.')


if __name__ == '__main__':
    try:
        main()
    except Blocked as e:
        raise SystemExit(str(e))
