"""Permit automatic staging only for successful trusted main push CI, at current HEAD."""
import json
import os
import re
from pathlib import Path
from common import Blocked, SETTINGS, command


def release_from_event(event, repository):
    run=event.get('workflow_run',{})
    if repository != 'scalivoraai-hash/Mindaam' or run.get('head_repository',{}).get('full_name') != repository:
        raise Blocked('Automatic staging requires the authorised repository, never a fork')
    if run.get('name') != 'Validation' or run.get('event') != 'push' or run.get('head_branch') != 'main' or run.get('conclusion') != 'success':
        raise Blocked('Automatic staging requires successful main push application CI')
    sha=run.get('head_sha','')
    if not re.fullmatch('[a-f0-9]{40}',sha):raise Blocked('Automatic staging requires a complete release SHA')
    return sha


def main():
    if os.getenv('GITHUB_EVENT_NAME') != 'workflow_run':raise Blocked('This gate accepts only workflow_run events')
    sha=release_from_event(json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text()),SETTINGS['repository'])
    if command(['git','rev-parse','HEAD']) != sha:raise Blocked('Checkout does not match the validated source')
    current=command(['gh','api',f"repos/{SETTINGS['repository']}/commits/main",'--jq','.sha'])
    if current != sha:raise Blocked('Newer main exists; do not deploy an outdated automatic release')
    print('Trusted current main verified for staging: '+sha)

if __name__=='__main__':
    try:main()
    except Blocked as error:raise SystemExit(str(error))
