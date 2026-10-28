"""Explicit, expiring beta exception. Full-release evidence is never relabelled."""
import datetime
import json
import os
from common import HERE, Blocked
POLICY = json.loads((HERE / 'beta-policy.json').read_text())
BETA = POLICY['profile']

def profile():
    value = os.getenv('RELEASE_PROFILE', 'full')
    if value not in ('full', BETA):
        raise Blocked('Unknown release profile')
    if value == BETA and datetime.date.today() > datetime.date.fromisoformat(POLICY['expires_on']):
        raise Blocked('Limited-beta approval window expired; a new reviewed policy is required')
    return value

def evidence_name(value=None):
    return 'staging-beta-verified.json' if (value or profile()) == BETA else 'staging-verified.json'

def review_name(value=None):
    return 'beta-release-review.json' if (value or profile()) == BETA else 'release-review.json'

def required_checks(value):
    checks = json.loads((HERE / 'acceptance-checks.json').read_text())
    if value == BETA:
        return [x for x in checks if x != 'venue_booking'] + POLICY['additional_checks']
    return checks

def validate_beta(evidence, review=None, *, relay_attempt=False):
    if evidence.get('profile') != BETA or evidence.get('deferred') != POLICY['deferred']:
        raise Blocked('Beta evidence must identify every deferred payment test')
    if any(evidence.get('checks', {}).get(k) is True for k in POLICY['deferred']):
        raise Blocked('Deferred payment tests must never be represented as PASS')
    expected = [k for k in required_checks(BETA) if not (relay_attempt and k == 'direct_webrtc')]
    if not all(evidence.get('checks', {}).get(k) is True for k in expected):
        raise Blocked('Non-payment beta acceptance is incomplete')
    if review is not None:
        if review.get('profile') != BETA or review.get('deferred') != POLICY['deferred'] or review.get('payment_actions_enabled') is not False:
            raise Blocked('Review does not match gated beta policy')
        security = review.get('security_review', {})
        if any(security.get(k) is not True for k in ('owner_access_verified','production_secrets_verified','database_isolation_verified','backup_restore_verified','public_launch_safeguards_verified')):
            raise Blocked('Actual owner, secrets, isolation, backup restore and public-launch security review required')
        if not security.get('evidence_object') or not security['evidence_object'].endswith('/security-review.json'):
            raise Blocked('Private security-review evidence reference required')
