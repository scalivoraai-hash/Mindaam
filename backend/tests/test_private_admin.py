from sqlalchemy import select, func
from backend.tests.test_core import system, register
from backend.api.models import User, Session, Audit
from backend.api.operations import bootstrap_owner
from backend.api.main import local_buckets

TEMP = 'Disposable-local-only-owner-secret-123!'
PERMANENT = 'Changed-local-only-owner-secret-456!'

def owner(dbs, monkeypatch):
    monkeypatch.setenv('SUPER_ADMIN_EMAIL', 'owner@example.test')
    monkeypatch.setenv('SUPER_ADMIN_USERNAME', 'private_owner')
    monkeypatch.setenv('SUPER_ADMIN_INITIAL_PASSWORD', TEMP)
    with dbs.begin() as db:
        bootstrap_owner(db)
        bootstrap_owner(db)
        assert db.scalar(select(func.count()).select_from(User).where(User.role=='super_admin')) == 1

def test_private_admin_complete_password_session_and_rbac(system, monkeypatch):
    c, dbs = system
    h, u = register(c, 'ordinary_private')
    assert c.get('/api/super-admin/overview').status_code == 401
    assert c.get('/api/super-admin/overview', headers=h).status_code == 403
    assert c.post('/api/auth/admin-login', json={'identifier':u['email'],'password':'A secure test password 2026!'}).status_code == 401
    owner(dbs, monkeypatch)
    wrong=c.post('/api/auth/admin-login',json={'identifier':'private_owner','password':'wrong'})
    unknown=c.post('/api/auth/admin-login',json={'identifier':'unknown','password':'wrong'})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    login=c.post('/api/auth/admin-login',json={'identifier':'OWNER@example.test','password':TEMP})
    assert login.status_code == 200
    assert login.json()['user']['must_change_password']
    ah={'Authorization':'Bearer '+login.json()['token']}
    assert c.get('/api/super-admin/overview',headers=ah).status_code == 403
    for pw in ['short',TEMP]:
        assert c.post('/api/auth/change-password',headers=ah,json={'current_password':TEMP,'password':pw,'confirm_password':pw}).status_code == 422
    assert c.post('/api/auth/change-password',headers=ah,json={'current_password':TEMP,'password':PERMANENT,'confirm_password':PERMANENT}).status_code == 200
    assert c.get('/api/me',headers=ah).status_code == 401
    assert c.post('/api/auth/admin-login',json={'identifier':'private_owner','password':TEMP}).status_code == 401
    headers={'Origin':'http://localhost:3000','X-Pulse-Client':'web'}
    login=c.post('/api/auth/admin-login',headers=headers,json={'identifier':'private_owner','password':PERMANENT})
    assert login.status_code == 200 and 'token' not in login.json()
    assert 'HttpOnly' in login.headers['set-cookie']
    assert c.get('/api/me').json()['role']=='super_admin'
    for path in ['overview','worlds','users','audit','collectibles']:
        assert c.get('/api/super-admin/'+path).status_code==200
    assert c.post('/api/auth/logout',headers=headers).status_code==200
    assert c.get('/api/me').status_code==401
    with dbs() as db:
        actions=set(db.scalars(select(Audit.action)))
        assert {'owner.bootstrap','identity.admin_login','identity.password_changed'} <= actions

def test_bootstrap_refuses_elevation(system, monkeypatch):
    c, dbs=system
    h,u=register(c,'ordinary_owner')
    monkeypatch.setenv('SUPER_ADMIN_EMAIL',u['email'])
    monkeypatch.setenv('SUPER_ADMIN_USERNAME',u['username'])
    monkeypatch.setenv('SUPER_ADMIN_INITIAL_PASSWORD',TEMP)
    import pytest
    with pytest.raises(RuntimeError,match='refusing automatic privilege escalation'):
        with dbs.begin() as db:bootstrap_owner(db)


def test_admin_login_rate_limit(system, monkeypatch):
    # The fixture has its own client IP; no registration consumes its auth quota.
    # Pin the middleware clock so a Redis minute boundary cannot reset this test.
    import time
    from types import SimpleNamespace
    import backend.api.main as main_module
    fixed = time.time()
    monkeypatch.setattr(main_module, 'time', SimpleNamespace(time=lambda: fixed))
    c, _ = system
    local_buckets.clear()
    for _ in range(20):
        assert c.post('/api/auth/admin-login',json={'identifier':'unknown','password':'wrong'}).status_code==401
    limited=c.post('/api/auth/admin-login',json={'identifier':'unknown','password':'wrong'})
    assert limited.status_code==429 and limited.headers['Retry-After']=='60'

def test_owner_inspection_does_not_change_roles(system, monkeypatch):
    from backend.api.owner_access import inspect
    c, dbs=system
    _,u=register(c,'inspection_player')
    with dbs() as db:
        result=inspect(db,u['email'])
        assert result['requested_identity_exists']
        assert not result['requested_identity_is_super_admin']
        assert db.get(User,u['id']).role=='consumer'
    owner(dbs,monkeypatch)
    with dbs() as db:
        result=inspect(db,'owner@example.test')
        assert result['sole_owner_matches_requested_identity']
        assert result['requested_identity_requires_password_change']
