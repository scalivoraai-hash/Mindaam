"""Exercise the real JWT parser used by OAuth and LiveKit after security upgrades."""
import base64
import sys
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from sqlalchemy import func, select

from backend.api import oauth
from backend.api.models import Session, User
from backend.tests.test_core import system


def nested_token():
    def segment(value):
        return base64.urlsafe_b64encode(value.encode()).rstrip(b'=').decode()
    return '.'.join([
        segment('{"alg":"RS256","kid":"untrusted"}'),
        segment('{"nested":' + '[' * (sys.getrecursionlimit() * 10) + '0'
                + ']' * (sys.getrecursionlimit() * 10) + '}'),
        segment('untrusted-signature'),
    ])


def test_oauth_nested_payload_fails_closed_before_jwks_fetch(system, monkeypatch):
    """CVE-2026-101918 must enter the existing PyJWTError handler, not return 500."""
    client, sessions = system
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'jwt-regression-client')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'jwt-regression-secret')
    monkeypatch.setenv('PUBLIC_ORIGIN', 'http://testserver')
    with sessions() as db:
        before = [db.scalar(select(func.count()).select_from(model)) for model in (User, Session)]

    class Provider:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            return SimpleNamespace(raise_for_status=lambda: None,
                                   json=lambda: {'id_token': nested_token()})

    def unexpected_fetch(*args, **kwargs):
        pytest.fail('Malformed JWT reached JWKS network lookup')

    monkeypatch.setattr(oauth.httpx, 'Client', Provider)
    monkeypatch.setattr(jwt.PyJWKClient, 'fetch_data', unexpected_fetch)
    start = client.get('/api/oauth/google/start?adult=true&terms=true', follow_redirects=False)
    state = parse_qs(urlparse(start.headers['location']).query)['state'][0]
    callback = client.get('/api/oauth/google/callback',
                          params={'state': state, 'code': 'test-only'}, follow_redirects=False)
    assert callback.status_code == 303
    assert callback.headers['location'] == '/?oauth_error=provider_failed'
    assert 'pulse-oauth-grant' not in callback.cookies
    assert client.get('/api/oauth/google/callback', params={'state': state, 'code': 'replay'},
                      follow_redirects=False).status_code == 403
    with sessions() as db:
        assert [db.scalar(select(func.count()).select_from(model)) for model in (User, Session)] == before


def test_nested_unverified_decode_raises_documented_jwt_error():
    with pytest.raises(jwt.DecodeError):
        jwt.decode(nested_token(), options={'verify_signature': False})


def test_livekit_sdk_tokens_verify_and_reject_tampering():
    from livekit.api import AccessToken, TokenVerifier, VideoGrants
    secret = 'local-regression-secret-at-least-32-characters'
    verifier = TokenVerifier('local-regression-key', secret)
    token = (AccessToken('local-regression-key', secret).with_identity('regression-user')
             .with_grants(VideoGrants(room_join=True, room='regression-room')).to_jwt())
    claims = verifier.verify(token)
    assert claims.identity == 'regression-user'
    assert claims.video.room == 'regression-room'
    with pytest.raises(jwt.InvalidSignatureError):
        TokenVerifier('local-regression-key', secret + '-wrong').verify(token)
    with pytest.raises(jwt.InvalidIssuerError):
        TokenVerifier('wrong-key', secret).verify(token)
    expired = jwt.encode({'sub': 'regression-user', 'iss': 'local-regression-key',
                          'exp': int(time.time()) - 3600}, secret, algorithm='HS256')
    with pytest.raises(jwt.ExpiredSignatureError):
        verifier.verify(expired)
