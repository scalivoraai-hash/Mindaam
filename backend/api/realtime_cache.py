"""Per-connection state reuse, invalidated after committed authoritative changes.

Redis shares only a revision, never a private user's snapshot or bearer token.
Time-driven active media and bus travel retain the original sampling cadence.
"""
import logging
import time
from threading import Lock
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session as ORMSession

KEY = 'mindaam:state-revision:v1'
MAX_AGE = 5.0
_lock = Lock()
_revision = 0
_redis = None
# These records do not alter the realtime payload or authorization.
IGNORED = {'Audit', 'Analytics', 'UserActivity', 'OnlineSample', 'MotionDiagnostic'}
HEARTBEAT_FIELDS = {'Presence': {'updated_at'}, 'Attendee': {'last_seen'}}

def configure(client):
    global _redis
    _redis = client

def revision():
    # Redis failure is fail-closed: the websocket closes, rather than serving stale state.
    if _redis is not None: return _redis.get(KEY) or b'0'
    with _lock: return _revision

def changed():
    global _revision
    with _lock: _revision += 1
    if _redis is not None: _redis.incr(KEY)

@event.listens_for(ORMSession, 'before_flush')
def remember_changes(db, *_):
    for row in list(db.new) + list(db.deleted):
        if type(row).__name__ not in IGNORED: db.info['mindaam_state_changed'] = True
    for row in db.dirty:
        name=type(row).__name__
        if name in IGNORED: continue
        fields={a.key for a in inspect(row).attrs if a.history.has_changes()}
        if fields - HEARTBEAT_FIELDS.get(name,set()): db.info['mindaam_state_changed'] = True

@event.listens_for(ORMSession, 'do_orm_execute', retval=True)
def bulk_changes(execution):
    result=execution.invoke_statement()
    if (execution.is_update or execution.is_delete or execution.is_insert) and getattr(result,'rowcount',-1)!=0:
        execution.session.info['mindaam_state_changed']=True
    return result

@event.listens_for(ORMSession, 'after_commit')
def committed(db):
    if db.info.pop('mindaam_state_changed',False): changed()

@event.listens_for(ORMSession, 'after_rollback')
def rolled_back(db): db.info.pop('mindaam_state_changed',None)

class StateCache:
    """Bounded to one socket, so responses cannot leak between users or grow globally."""
    def __init__(self, allow_local=False):
        self.enabled=_redis is not None or allow_local
        self.value=None; self.revision=None; self.until=0; self.expires_at=0
        self.hits=0; self.misses=0
    def read(self, build, now=None):
        now=time.monotonic() if now is None else now
        if not self.enabled:
            self.misses+=1
            return build()[0]
        before=revision()
        if self.value is not None and before==self.revision and now<self.until and time.time()<self.expires_at:
            self.hits+=1
            return self.value
        self.misses+=1
        value,expires_at=build()
        after=revision()
        dynamic=bool(value.get('journey') or any(p.get('vehicle',{} ) and p['vehicle'].get('kind')=='bus' for p in value.get('players',[])) or any(m.get('state')=='accepted' for m in value.get('media',[])))
        self.value=value; self.expires_at=expires_at
        # A concurrent transaction may have changed auth/state during the build.
        # Never label the preceding snapshot with that new revision.
        self.revision=before
        self.until=now+(MAX_AGE if before==after and not dynamic else 0)
        return value
