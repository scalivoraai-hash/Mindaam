import time
import jwt
from backend.tests.test_core import system
from backend.tests.test_talk import pair
from backend.api.models import MediaSession
from backend.api import main


def test_voice_video_grants_and_end_revocation(system, monkeypatch):
    c, db, a, ua, b, ub = pair(system)
    monkeypatch.setenv('LIVEKIT_URL', 'wss://media.example.test')
    monkeypatch.setenv('LIVEKIT_API_KEY', 'test-key')
    secret = 'test-only-secret-at-least-thirty-two-characters'
    monkeypatch.setenv('LIVEKIT_API_SECRET', secret)
    cleaned = []
    async def cleanup(id):
        cleaned.append(id)
    monkeypatch.setattr(main.media, 'terminate_room', cleanup)
    for kind, sources in [('voice', ['microphone']), ('liveface', ['camera', 'microphone'])]:
        s = c.post('/api/talk/request', headers=a, json={'target_id': ub['id'], 'kind': kind}).json()
        assert c.post('/api/media/'+s['id']+'/token', headers=a).status_code == 403
        assert c.post('/api/talk/'+s['id']+'/accept', headers=b).status_code == 200
        for h, user in [(a, ua), (b, ub)]:
            grant = c.post('/api/media/'+s['id']+'/token', headers=h).json()
            claims = jwt.decode(grant['token'], secret, algorithms=['HS256'], issuer='test-key')
            assert claims['sub'] == user['id']
            assert claims['video']['room'] == 'pulse-'+s['id']
            assert claims['video']['canPublishSources'] == sources
            assert claims['exp']-claims['nbf'] <= 60
            assert secret not in str(grant)
        assert c.post('/api/talk/'+s['id']+'/end', headers=a).status_code == 409
        assert c.post('/api/media/'+s['id']+'/end', headers=a).status_code == 200
        assert s['id'] in cleaned
        assert c.post('/api/media/'+s['id']+'/token', headers=b).status_code == 403
        assert s['id'] in main.maintenance()


def test_expired_media_cannot_rejoin(system, monkeypatch):
    c, db, a, ua, b, ub = pair(system)
    s = c.post('/api/talk/request', headers=a, json={'target_id': ub['id'], 'kind':'voice'}).json()
    c.post('/api/talk/'+s['id']+'/accept', headers=b)
    with db.begin() as d:
        d.get(MediaSession, s['id']).accepted_at = time.time()-601
    assert c.post('/api/media/'+s['id']+'/token', headers=a).status_code == 409
    assert s['id'] in main.maintenance()
