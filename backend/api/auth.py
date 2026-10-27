import os
import hashlib
import secrets
import time
import bcrypt
from fastapi import Depends, HTTPException, Header, Request, Response
from sqlalchemy import select
from .db import get_db
from .models import User, Session


def hash_password(password):
    return bcrypt.hashpw(
        hashlib.sha256(password.encode()).digest(), bcrypt.gensalt(rounds=12)
    ).decode()


def check_password(password, hashed):
    return bcrypt.checkpw(hashlib.sha256(password.encode()).digest(), hashed.encode())


def session_token(db, user):
    token = secrets.token_urlsafe(40)
    db.add(
        Session(
            id=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=time.time() + 86400,
        )
    )
    return token


def user_for_token(db, token):
    s = db.get(Session, hashlib.sha256(token.encode()).hexdigest())
    if not s or s.expires_at < time.time():
        raise HTTPException(401, "Session expired. Please sign in.")
    u = db.get(User, s.user_id)
    if not u or u.suspended:
        raise HTTPException(403, "Account unavailable")
    return u


COOKIE_NAME = 'pulse-session'

def request_token(request, authorization=''):
    return authorization[7:] if authorization.startswith('Bearer ') else request.cookies.get(COOKIE_NAME, '')

def check_browser_origin(request):
    expected = os.getenv('PUBLIC_ORIGIN', 'http://localhost:3000').rstrip('/')
    if request.headers.get('origin') != expected or request.headers.get('x-pulse-client') != 'web':
        raise HTTPException(403, 'Reload Mindaam and try again')

def login_result(db, user, request, response):
    token = session_token(db, user)
    if request.headers.get('x-pulse-client') == 'web':
        check_browser_origin(request)
        response.set_cookie(COOKIE_NAME, token, max_age=86400, httponly=True,
                            secure=os.getenv('PUBLIC_ORIGIN','').startswith('https://'), samesite='lax', path='/')
        return {'user': public_user(user)}
    return {'token': token, 'user': public_user(user)}

def current_user(request: Request, authorization: str = Header(default=''), db=Depends(get_db)):
    token = request_token(request, authorization)
    if not token:
        raise HTTPException(401, 'Please sign in')
    if not authorization.startswith('Bearer ') and request.method not in {'GET','HEAD','OPTIONS'}:
        check_browser_origin(request)
    return user_for_token(db, token)


def require_admin(user=Depends(current_user)):
    if user.must_change_password:raise HTTPException(403,"Change your initial password first")
    if user.role not in {"admin", "super_admin"}:
        raise HTTPException(403, "Administrator access required")
    return user


def public_user(u):
    return {
        k: getattr(u, k)
        for k in (
            "id",
            "email",
            "verified",
            "username",
            "city",
            "avatar",
            "profile",
            "privacy",
            "interests",
            "onboarded",
            "role",
            "must_change_password",
            "location_consent",
            "analytics_consent",
        )
    }


def display_profile(u):
    """Whitelist opt-in descriptive fields; never expose private identity or coordinates."""
    p = u.profile or {}
    result = {k:p[k] for k in ('display_name','bio','public_interests','languages','category','theme') if k in p}
    result['links'] = {k:v['url'] for k,v in p.get('links', {}).items() if isinstance(v,dict) and v.get('visible') and v.get('url')}
    if p.get('show_location'):
        result['display_location'] = {k:p.get(k,'') for k in ('country','town','area')}
    if p.get('show_identity'):
        result['identity'] = p.get('custom_identity') if p.get('identity') == 'Custom / Other' else p.get('identity','Prefer not to say')
    return result
