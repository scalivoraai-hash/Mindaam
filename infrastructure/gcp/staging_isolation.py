"""Read-only evidence that a staging release left production revision/traffic unchanged."""
import json
import os
import subprocess
import sys
from pathlib import Path


def fingerprint(service, revision):
    status = service['status']
    return {
        'service': service['metadata']['name'],
        'ready_revision': status['latestReadyRevisionName'],
        'latest_revision': status['latestCreatedRevisionName'],
        'image_digest': revision['status']['imageDigest'],
        'traffic': sorted(json.loads(json.dumps(status.get('traffic', []))), key=lambda row: json.dumps(row, sort_keys=True)),
    }


def main():
    if os.environ.get('OPERATION') != 'staging' or os.environ.get('MINDAAM_PROJECT_ID') != 'mindaam':
        raise RuntimeError('This read-only comparison is restricted to the existing Mindaam staging operation')
    phase = sys.argv[1]
    if phase not in {'before', 'after'}:
        raise ValueError('Expected before or after')
    def describe(kind, name):
        return json.loads(subprocess.check_output([
            'gcloud', 'run', kind, 'describe', name, '--project', 'mindaam',
            '--region', 'europe-west2', '--format=json'], text=True))
    service = describe('services', 'mindaam-production')
    snapshot = fingerprint(service, describe('revisions', service['status']['latestReadyRevisionName']))
    out = Path('gcp-evidence'); out.mkdir(exist_ok=True)
    (out / ('production-' + phase + '.json')).write_text(json.dumps(snapshot, indent=2) + '\n')
    if phase == 'after':
        if snapshot != json.loads((out / 'production-before.json').read_text()):
            raise RuntimeError('Production revision, image or traffic changed during staging release; inspect evidence')
        print('Production revision, image digest and traffic unchanged')


if __name__ == '__main__':
    main()
