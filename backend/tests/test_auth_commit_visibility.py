"""A successful cookie response must not race its session transaction."""
import hashlib
from http.cookies import SimpleCookie
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.api import core,main
from backend.api.db import get_db
from backend.api.models import Session,User
from sqlalchemy import select
from backend.tests.test_core import system

def test_registration_cookie_is_committed_before_response_starts(system):
    _,sessions=system
    app=FastAPI();app.include_router(core.router)
    app.dependency_overrides[get_db]=main.app.dependency_overrides[get_db]
    visible=[]
    async def observe(scope,receive,send):
        async def capture(message):
            if message['type']=='http.response.start':
                for key,value in message.get('headers',[]):
                    if key==b'set-cookie':
                        cookies=SimpleCookie();cookies.load(value.decode())
                        if 'pulse-session' in cookies:
                            digest=hashlib.sha256(cookies['pulse-session'].value.encode()).hexdigest()
                            with sessions() as db:visible.append(db.get(Session,digest) is not None)
            await send(message)
        await app(scope,receive,capture)
    headers={'Origin':'http://localhost:3000','X-Pulse-Client':'web'}
    with TestClient(observe) as client:
        response=client.post('/api/auth/register',headers=headers,json={
            'email':'commit_visibility@example.test','username':'commit_visibility',
            'password':'A secure test password 2026!','confirm_password':'A secure test password 2026!',
            'adult':True,'accepted_terms':True,'accepted_privacy':True})
        assert response.status_code==201,response.text
        assert visible==[True],'Cookie was published before its session became visible to another transaction'
        login={'identifier':'commit_visibility','password':'A secure test password 2026!'}
        response=client.post('/api/auth/login',headers=headers,json=login)
        assert response.status_code==200,response.text
        assert visible==[True,True]
        with sessions.begin() as db:
            db.scalar(select(User).where(User.username=='commit_visibility')).role='super_admin'
        response=client.post('/api/auth/admin-login',headers=headers,json=login)
        assert response.status_code==200,response.text
        assert visible==[True,True,True]

def test_failed_registration_commit_cannot_publish_success_or_cookie(system):
    _,sessions=system
    app=FastAPI();app.include_router(core.router)
    def failed_commit():
        with sessions() as db:
            yield db
            raise RuntimeError('Injected commit failure')
    app.dependency_overrides[get_db]=failed_commit
    with TestClient(app,raise_server_exceptions=False) as client:
        response=client.post('/api/auth/register',headers={'Origin':'http://localhost:3000','X-Pulse-Client':'web'},json={
            'email':'commit_failure@example.test','username':'commit_failure',
            'password':'A secure test password 2026!','confirm_password':'A secure test password 2026!',
            'adult':True,'accepted_terms':True,'accepted_privacy':True})
    assert response.status_code==500
    assert 'pulse-session' not in response.cookies
    with sessions() as db:
        assert db.scalar(select(User).where(User.username=='commit_failure')) is None
