"""Dispatch immutable, resumable releases; all subprocess inputs are separate argv."""
import json
import os
import re
import subprocess
from pathlib import Path
from common import Cloud, Blocked, SETTINGS, command, summary
from deploy import foundation, deploy, rollback, image_check
from smoke import check


def main():
    operation = os.environ['OPERATION']
    c = Cloud(os.environ['MINDAAM_PROJECT_ID']); c.require_project()
    sha = os.environ['RELEASE_SHA']
    if not re.fullmatch(r'[a-f0-9]{40}', sha):
        raise Blocked('A complete release SHA is required')
    # Old release references are allowed only if still present in this repository's main history.
    if subprocess.run(['git', 'merge-base', '--is-ancestor', sha, 'HEAD'], capture_output=True).returncode:
        raise Blocked('Release is not in Mindaam main history')
    if operation == 'foundation':
        foundation(c); return
    if operation == 'rollback':
        rollback(c, sha); return
    if operation == 'staging':
        if sha != command(['git', 'rev-parse', 'HEAD']):
            raise Blocked('Build staging from current main; verify/production can resume an existing SHA')
        if not c.get_json('foundation.json'):
            raise Blocked('Complete foundation and media/turn DNS first')
        existing = c.get_json(f'releases/{sha}/staging.json')
        image = existing.get('image') if existing else None
        if not image:
            registry = c.region + '-docker.pkg.dev'
            tag = f'{registry}/{c.project}/mindaam/app:{sha}'
            c.gc('auth', 'configure-docker', registry, raw=True)
            # No shell, no build arguments containing secrets, no unreviewed application checkout.
            subprocess.run(['docker', 'build', '-f', 'infrastructure/gcp/Dockerfile', '-t', tag, '.'], check=True)
            subprocess.run(['docker', 'push', tag], check=True)
            info = c.gc('artifacts', 'docker', 'images', 'describe', tag)
            digest = info['image_summary']['digest']
            image = tag.rsplit(':', 1)[0] + '@' + digest
        image_check(c, image)
        deploy(c, 'staging', image, sha)
    elif operation == 'verify':
        release = c.get_json(f'releases/{sha}/staging.json')
        if not release:
            raise Blocked('No existing staging release for this SHA')
        current = c.gc("run", "services", "describe", "mindaam-staging", "--region=" + c.region)
        if current["status"]["latestReadyRevisionName"] != release["revision"]:
            raise Blocked("Requested staging revision is no longer current")
        Path('deployment-result.json').write_text(json.dumps(release, indent=2))
    elif operation == 'production':
        staged = c.get_json(f'releases/{sha}/staging-verified.json')
        if not staged:
            raise Blocked('Actual staging acceptance is required')
        object_name = os.getenv('REVIEW_OBJECT', '')
        expected = f'releases/{sha}/release-review.json'
        if object_name != expected:
            raise Blocked('Select the exact private release review prepared for this SHA: ' + expected)
        deploy(c, 'production', staged['image'], sha)
    else:
        raise Blocked('Unknown operation')
    release = json.loads(Path('deployment-result.json').read_text())
    result = check(release)
    Path('smoke-result.json').write_text(json.dumps(result, indent=2))
    if operation == 'production':
        # Verify provider URL too; it serves the app but authenticated browser flows use mindaam.com.
        check({**release, 'origin': release['provider_origin']})
        c.put_json(f'releases/{sha}/production-verified.json', {**release, 'smoke': result})
        summary('Production URL and health verified: ' + release['origin'] + '\nGCP production URL: ' + release['provider_origin'] + '\nMedia: https://' + SETTINGS['media_domain'])


if __name__ == '__main__':
    try:
        main()
    except Blocked as e:
        raise SystemExit(str(e))
