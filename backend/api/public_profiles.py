"""Shared, authenticated social-profile view. Identity remains keyed by user UUID."""
import time
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, func
from .auth import current_user, display_profile
from .db import get_db
from .models import User, Social, Presence, Event
from .world import blocked, friends

router = APIRouter(prefix='/api/profiles')


def visible(db, viewer, person):
    return bool(person and not person.suspended and (person.id == viewer.id or (
        person.onboarded and not blocked(db, viewer.id, person.id)
        and person.privacy not in {'Ghost Mode', 'Event Mode'}
        and (person.privacy != 'Friends Only' or friends(db, viewer.id, person.id)))))


def profile_view(db, viewer, person):
    if not visible(db, viewer, person):
        raise HTTPException(404, 'Profile unavailable')
    outgoing = set(db.scalars(select(Social.kind).where(Social.actor==viewer.id, Social.target==person.id)))
    incoming = set(db.scalars(select(Social.kind).where(Social.actor==person.id, Social.target==viewer.id)))
    count = lambda *clauses: db.scalar(select(func.count()).select_from(Social).where(*clauses)) or 0
    presence = db.get(Presence, person.id)
    events = db.scalars(select(Event).where(Event.host_id==person.id, Event.visibility=='public').order_by(Event.starts_at.desc()).limit(30)).all()
    return {
        'id': person.id, 'username': person.username, 'avatar': person.avatar,
        **display_profile(person), 'joined_at': person.created_at,
        'photos': {k: '/api/profiles/'+person.id+'/photos/'+k+'?v='+str((person.profile or {})[k+'_version']) for k in ('picture','cover') if (person.profile or {}).get(k+'_version')},
        'own': person.id == viewer.id,
        'online': bool(presence and presence.updated_at > time.time()-45 and person.privacy not in {'Ghost Mode','Event Mode'}),
        'relationship': {'following': 'follow' in outgoing, 'friend': friends(db, viewer.id, person.id),
                         'requested': 'request' in outgoing, 'incoming': 'request' in incoming},
        'counts': {'followers': count(Social.target==person.id, Social.kind=='follow'),
                   'following': count(Social.actor==person.id, Social.kind=='follow'),
                   'friends': count(Social.actor==person.id, Social.kind=='friend'),
                   'events': db.scalar(select(func.count()).select_from(Event).where(Event.host_id==person.id,Event.visibility=='public')) or 0},
        'events': [{'id': e.id, 'title': e.title, 'starts_at': e.starts_at, 'state': e.status} for e in events],
    }


@router.get('/by-name/{username}')
def by_name(username: str, response: Response, u=Depends(current_user), db=Depends(get_db)):
    response.headers['Cache-Control'] = 'private, no-store'
    person = db.scalar(select(User).where(func.lower(func.trim(User.username))==username.strip().lower()))
    return profile_view(db, u, person)


@router.get('/{user_id}')
def by_id(user_id: str, response: Response, u=Depends(current_user), db=Depends(get_db)):
    response.headers['Cache-Control'] = 'private, no-store'
    return profile_view(db, u, db.get(User, user_id))
