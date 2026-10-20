"""Source-specific screen permission within the existing Event and LiveKit room.

Only a provider-confirmed source can take the wall. Layout never enters this API.
A pending picker does not evict the previous presenter; confirmation switches it.
"""
import asyncio
import logging
import os
import time
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from .auth import current_user
from .core import Strict
from .db import get_db
from .models import Event, Attendee, Audit
from . import events, media

router = APIRouter(prefix='/api/events')
log = logging.getLogger('pulseworld')
LEASE_SECONDS = 40
PICKER_SECONDS = 120
LIGHT_PRESETS = ['STANDARD','CONCERT','DJ PARTY','CINEMA','WARM','COOL','PURPLE WAVE','BLUE WAVE','RAINBOW','SPOTLIGHT','PULSE']
DEFAULT_LIGHTING = {'enabled':True,'preset':'STANDARD','intensity':.7,'target':'stage'}


def touch_permission(a):
    a.permission_dirty = True
    a.permission_revision = (a.permission_revision or 0) + 1


def effective_share(e, a, now=None):
    if not a or a.state != 'active' or e.status != 'live': return False
    now = time.time() if now is None else now
    state = e.presentation or {}
    return (a.user_id == state.get('presenter_id') and state.get('lease_until',0)>now or
            a.user_id == state.get('pending_id') and state.get('pending_until',0)>now)


def expire(db, e):
    state = dict(e.presentation or {}); now=time.time(); changed=set()
    for key, deadline in [('presenter_id','lease_until'),('pending_id','pending_until')]:
        uid=state.get(key); a=db.get(Attendee,(e.id,uid)) if uid else None
        if uid and (e.status!='live' or not a or a.state!='active' or state.get(deadline,0)<=now):
            changed.add(uid)
            if key=='presenter_id':
                for k in ['presenter_id','screen_track_id','screen_audio_track_id','started_at','lease_until']:state.pop(k,None)
            else:
                for k in ['pending_id','pending_until','request_id']:state.pop(k,None)
    if changed:
        state['revision']=state.get('revision',0)+1;e.presentation=state
        for uid in changed:
            if a:=db.get(Attendee,(e.id,uid)):touch_permission(a)
        log.info('event presentation expired',extra={'event_id':e.id})


def state_view(e, a=None, moderator=False):
    state = e.presentation or {}; now=time.time()
    presenter = state.get('presenter_id') if state.get('lease_until',0)>now else None
    pending = state.get('pending_id') if state.get('pending_until',0)>now else None
    return {'presenter_id':presenter,'screen_track_id':state.get('screen_track_id') if presenter else None,
            'screen_audio_track_id':state.get('screen_audio_track_id') if presenter else None,
            'pending_id':pending,'revision':state.get('revision',0),
            'started_at':state.get('started_at') if presenter else None,
            'stage_wall_mode':'SCREEN_SHARE' if presenter else 'ACTIVE_SPEAKER_VIDEO_OR_DEFAULT',
            'my_share_state':a.share_state if a else 'none',
            'may_start':bool(a and a.state=='active' and e.status=='live' and (moderator or a.share_state=='allowed') and (not presenter or presenter==a.user_id or pending==a.user_id or moderator)),
            'can_publish_screen':effective_share(e,a),
            'lighting':{**DEFAULT_LIGHTING,**(e.lighting or {})}}


def live(db, id, user, moderator=False):
    e=events.get(db,id,user,moderator);expire(db,e)
    a=db.get(Attendee,(id,user.id))
    if e.status!='live' or not a or a.state!='active':raise HTTPException(403,'Join the live event first')
    if e.communication_mode=='text':raise HTTPException(409,'This event has no media room')
    a.last_seen=time.time()
    return e,a


async def apply(db,e,ids):
    # Keep the locked event row while applying its current revision. No stale grant
    # can overtake a revoke. Failed provider changes remain dirty for maintenance.
    for uid in set(ids):
        a=db.get(Attendee,(e.id,uid))
        if not a or not e.session_id:continue
        try:
            await asyncio.wait_for(media.update_participant_permission(e.session_id,uid,
                a.state=='active' and a.role in ['host','cohost','speaker'],e.communication_mode,
                effective_share(e,a)),timeout=3)
            a.permission_dirty=False
        except Exception:
            a.permission_dirty=True
            log.warning('event source permission will retry',extra={'event_id':e.id,'user_id':uid})


@router.post('/{id}/presentation/request')
def request_share(id:str,u=Depends(current_user),db=Depends(get_db)):
    e,a=live(db,id,u)
    if a.share_state not in ['allowed','pending']:
        a.share_state='pending'
        events.notify(db,e.host_id,'event.screen_request',u.username+' would like to share a screen',id)
        db.add(Audit(actor_id=u.id,action='event.screen_requested',target=id))
    return state_view(e,a,events.host(db,e,u))


@router.post('/{id}/presentation/people/{user_id}/{action}')
def permission(id:str,user_id:str,action:Literal['allow','decline','revoke','switch'],u=Depends(current_user),db=Depends(get_db)):
    e,_=live(db,id,u,True);a=db.get(Attendee,(id,user_id))
    if not a or a.state!='active':raise HTTPException(409,'Participant has left the event')
    state=dict(e.presentation or {}); affected={user_id}
    if action in ['allow','switch']:
        a.share_state='allowed'
        if action=='switch':
            if state.get('pending_id'):affected.add(state['pending_id'])
            state.update(pending_id=user_id,pending_until=time.time()+PICKER_SECONDS)
            state.pop('request_id',None)
        events.notify(db,user_id,'event.screen_allowed','Screen sharing approved. Choose Share screen when ready.',id)
    else:
        a.share_state='none'
        if state.get('presenter_id')==user_id:
            for k in ['presenter_id','screen_track_id','screen_audio_track_id','lease_until','started_at']:state.pop(k,None)
        if state.get('pending_id')==user_id:
            for k in ['pending_id','pending_until','request_id']:state.pop(k,None)
    state['revision']=state.get('revision',0)+1;e.presentation=state
    for uid in affected:
        if p:=db.get(Attendee,(id,uid)):touch_permission(p)
    asyncio.run(apply(db,e,affected))
    db.add(Audit(actor_id=u.id,action='event.screen_'+action,target=id,details={'participant':user_id}))
    return events.view(db,e,u)


class Start(Strict):
    request_id:UUID


@router.post('/{id}/presentation/start')
def start(id:str,data:Start,u=Depends(current_user),db=Depends(get_db)):
    e,a=live(db,id,u)
    if not (events.host(db,e,u) or a.share_state=='allowed'):raise HTTPException(403,'Ask the host to allow screen sharing first')
    state=dict(e.presentation or {})
    if state.get('pending_id') not in [None,u.id]:raise HTTPException(409,'Another presenter is choosing a screen. Ask the host to switch.')
    if state.get('presenter_id') not in [None,u.id] and state.get('pending_id')!=u.id and not events.host(db,e,u):
        raise HTTPException(409,'A presentation is live. Ask the host to switch to you.')
    # Same deliberate gesture/request may retry safely. A different tab cannot
    # replace an in-flight picker for this identity.
    if state.get('pending_id')==u.id and state.get('request_id') not in [None,str(data.request_id)]:
        raise HTTPException(409,'A screen picker is already open for your account')
    state.update(pending_id=u.id,pending_until=time.time()+PICKER_SECONDS,request_id=str(data.request_id),revision=state.get('revision',0)+1)
    e.presentation=state;touch_permission(a);asyncio.run(apply(db,e,[u.id]))
    if a.permission_dirty:raise HTTPException(503,'Screen sharing is reconnecting. Please try again.')
    db.add(Audit(actor_id=u.id,action='event.screen_picker',target=id))
    return state_view(e,a,events.host(db,e,u))


class Published(Start):
    screen_track_id:str=Field(min_length=1,max_length=100)


async def provider_screen(session_id,user_id,sid):
    from livekit import api
    if not media.provider_ready():raise HTTPException(503,'Event media is unavailable. Please try again.')
    try:
        async with api.LiveKitAPI(os.environ['LIVEKIT_URL'],os.environ['LIVEKIT_API_KEY'],os.environ['LIVEKIT_API_SECRET']) as client:
            p=await asyncio.wait_for(client.room.get_participant(api.RoomParticipantIdentity(room='pulse-'+session_id,identity=user_id)),timeout=3)
            video=next((t for t in p.tracks if t.sid==sid and t.source==api.TrackSource.SCREEN_SHARE and not t.muted),None)
            if not video:raise HTTPException(409,'Your screen is not ready yet. Please try again.')
            sound=next((t.sid for t in p.tracks if t.source==api.TrackSource.SCREEN_SHARE_AUDIO and not t.muted),None)
            return sound
    except HTTPException:raise
    except Exception:raise HTTPException(503,'Event media is reconnecting. Please try again.')


@router.post('/{id}/presentation/published')
def published(id:str,data:Published,u=Depends(current_user),db=Depends(get_db)):
    e,a=live(db,id,u);state=dict(e.presentation or {})
    if state.get('presenter_id')==u.id and state.get('screen_track_id')==data.screen_track_id:
        return state_view(e,a,events.host(db,e,u))
    if state.get('pending_id')!=u.id or state.get('request_id')!=str(data.request_id):raise HTTPException(409,'Screen-sharing permission changed. Ask the host to try again.')
    audio=asyncio.run(provider_screen(e.session_id,u.id,data.screen_track_id))
    old=state.get('presenter_id')
    for k in ['pending_id','pending_until','request_id']:state.pop(k,None)
    state.update(presenter_id=u.id,active_request_id=str(data.request_id),screen_track_id=data.screen_track_id,screen_audio_track_id=audio,started_at=time.time(),lease_until=time.time()+LEASE_SECONDS,revision=state.get('revision',0)+1)
    e.presentation=state
    if old and old!=u.id:
        old_a=db.get(Attendee,(id,old))
        if old_a:touch_permission(old_a)
        asyncio.run(apply(db,e,[old]))
    db.add(Audit(actor_id=u.id,action='event.screen_published',target=id))
    log.info('event screen published',extra={'event_id':id,'user_id':u.id})
    return state_view(e,a,events.host(db,e,u))


class TrackState(Strict):
    screen_track_id:str=Field(default='',max_length=100)


@router.post('/{id}/presentation/heartbeat')
def heartbeat(id:str,data:TrackState,u=Depends(current_user),db=Depends(get_db)):
    e,a=live(db,id,u);state=dict(e.presentation or {})
    if state.get('presenter_id')!=u.id or state.get('screen_track_id')!=data.screen_track_id:raise HTTPException(409,'This presentation has ended')
    state['lease_until']=time.time()+LEASE_SECONDS;e.presentation=state
    return state_view(e,a,events.host(db,e,u))


@router.post('/{id}/presentation/stop')
def stop(id:str,data:Start,u=Depends(current_user),db=Depends(get_db)):
    e,a=live(db,id,u);state=dict(e.presentation or {})
    if state.get('presenter_id')==u.id and state.get('active_request_id')==str(data.request_id):
        for k in ['presenter_id','screen_track_id','screen_audio_track_id','lease_until','started_at']:state.pop(k,None)
    if state.get('pending_id')==u.id and state.get('request_id')==str(data.request_id):
        for k in ['pending_id','pending_until','request_id']:state.pop(k,None)
    state['revision']=state.get('revision',0)+1;e.presentation=state;touch_permission(a)
    asyncio.run(apply(db,e,[u.id]));db.add(Audit(actor_id=u.id,action='event.screen_stopped',target=id))
    return state_view(e,a,events.host(db,e,u))


class Lighting(Strict):
    enabled:bool=True
    preset:Literal['STANDARD','CONCERT','DJ PARTY','CINEMA','WARM','COOL','PURPLE WAVE','BLUE WAVE','RAINBOW','SPOTLIGHT','PULSE']='STANDARD'
    intensity:float=Field(default=.7,ge=0,le=1,allow_inf_nan=False)
    target:Literal['stage','audience','screen']='stage'


@router.put('/{id}/lighting')
def lighting(id:str,data:Lighting,u=Depends(current_user),db=Depends(get_db)):
    e=events.get(db,id,u,True)
    if e.status not in ['scheduled','live']:raise HTTPException(409,'This event has ended')
    e.lighting={**data.model_dump(),'updated_at':time.time()}
    db.add(Audit(actor_id=u.id,action='event.lighting',target=id,details=data.model_dump()))
    return e.lighting


def reconcile_permission(db,event_id,user_id):
    # Used by existing maintenance and role moderation: read + lock current state,
    # never apply a permission snapshot captured before a concurrent revoke.
    e=db.scalar(select(Event).where(Event.id==event_id).execution_options(populate_existing=True).with_for_update())
    if not e:return
    expire(db,e)
    a=db.get(Attendee,(event_id,user_id),populate_existing=True)
    if a:asyncio.run(apply(db,e,[user_id]))
