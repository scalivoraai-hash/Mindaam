import os
import time
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select, or_, and_
from .db import get_db
from .models import MediaSession, User, ConversationMember, Event, Attendee
from . import conversations
from .auth import current_user
from .core import Strict, serialize, notify, emit
from .world import blocked

router = APIRouter(prefix="/api")


class MediaRequest(Strict):
    target_id: str
    kind: str


def provider_ready():
    return all(
        os.getenv(k) for k in ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
    )


def get_session(db, u, id):
    s = db.scalar(select(MediaSession).where(MediaSession.id == id).with_for_update())
    if not s or (u.id not in {s.requester, s.target} and not conversations.member(db,s,u.id)):
        raise HTTPException(404, "Media session unavailable")
    own=conversations.member(db,s,u.id)
    if own and own.state=='left' and s.state=='accepted':raise HTTPException(403,'You have left this session')
    return s


@router.get("/media")
def sessions(u=Depends(current_user), db=Depends(get_db)):
    own_ids=select(ConversationMember.session_id).where(ConversationMember.user_id==u.id,ConversationMember.state.in_(['active','invited']))
    rows=db.scalars(select(MediaSession).where(or_(MediaSession.requester==u.id,MediaSession.target==u.id,MediaSession.id.in_(own_ids)),MediaSession.state.in_(['pending','accepted']),or_(MediaSession.created_at>time.time()-900,MediaSession.event_id!=None))).all()
    result=[]
    for s in rows:
        own=conversations.member(db,s,u.id)
        if own and own.state=='left':continue
        if any(blocked(db,u.id,m.user_id) for m in conversations.members(db,s) if m.user_id!=u.id):continue
        item=conversations.view(db,s,u)
        if s.event_id:
            attendee=db.get(Attendee,(s.event_id,u.id))
            item['event_role']=attendee.role if attendee else None
            from .event_presentation import state_view
            from .events import host as event_host
            event=db.get(Event,s.event_id)
            item['presentation']=state_view(event,attendee,event_host(db,event,u))
            item['event_description']=event.description
            item['can_manage_event']=event_host(db,event,u)
            item['event_speakers']=list(db.scalars(select(Attendee.user_id).where(Attendee.event_id==s.event_id,Attendee.state=='active',Attendee.role.in_(['host','cohost','speaker']))))
        result.append(item)
    return result



@router.post("/media/request")
def request_media(data: MediaRequest, u=Depends(current_user), db=Depends(get_db)):
    if data.kind not in {"voice", "liveface"}:
        raise HTTPException(422, "Unknown media kind")
    # One pair lock and kind-aware duplicate protection for both invitation APIs.
    from .talk import Invitation, request
    return request(Invitation(target_id=data.target_id,kind=data.kind),u,db)


@router.post("/media/{session_id}/accept")
def accept(session_id: str, u=Depends(current_user), db=Depends(get_db)):
    s = get_session(db, u, session_id)
    own=conversations.member(db,s,u.id)
    if s.state=='accepted' and own and own.state=='invited':
        if not s.accepted_at or time.time()-s.accepted_at>600:raise HTTPException(409,'Session expired')
        if any(blocked(db,u.id,m.user_id) for m in conversations.members(db,s)):raise HTTPException(403,'Interaction unavailable')
        own.state='active';own.joined_at=time.time();return conversations.view(db,s,u)
    if u.id != s.target:
        raise HTTPException(403, "Only the invited player can consent")
    if blocked(db, s.requester, s.target) or any(
        not (peer := db.get(User, user_id)) or peer.suspended
        for user_id in (s.requester, s.target)
    ):
        raise HTTPException(403, "Interaction unavailable")
    from .talk import allowed, rules
    if s.kind not in {"voice", "liveface"} or not allowed(db,db.get(User,s.requester),u,s.kind):
        raise HTTPException(403, "Privacy or proximity changed")
    if s.created_at < time.time() - rules()['request_seconds']:
        raise HTTPException(409, "Request expired")
    if s.state != "pending":
        raise HTTPException(409, "Request is no longer pending")
    s.state = "accepted"
    s.accepted_at = time.time()
    conversations.members(db,s)
    notify(
        db, s.requester, "media_accepted", u.username + " accepted your request", s.id
    )
    return {**serialize(s), "provider_ready": provider_ready()}


@router.post("/media/{session_id}/reject")
def reject(session_id: str, u=Depends(current_user), db=Depends(get_db)):
    s = get_session(db, u, session_id)
    own=conversations.member(db,s,u.id)
    if own and own.state=='invited':
        own.state='left';own.left_at=time.time();own.reason='declined';return conversations.view(db,s,u)
    if s.state != "pending":
        raise HTTPException(409, "Request no longer pending")
    s.state = "rejected"
    s.ended_at = time.time()
    return serialize(s)


async def terminate_room(id):
    if not provider_ready():
        return
    from livekit import api

    async with api.LiveKitAPI(
        os.environ["LIVEKIT_URL"],
        os.environ["LIVEKIT_API_KEY"],
        os.environ["LIVEKIT_API_SECRET"],
    ) as client:
        try:
            await client.room.delete_room(api.DeleteRoomRequest(room="pulse-" + id))
        except api.TwirpError as e:
            if e.code != "not_found":
                raise HTTPException(
                    502,
                    "Video provider unavailable. Disable your camera and microphone; retry disconnect.",
                )


@router.post("/media/{session_id}/end")
async def end(session_id: str, u=Depends(current_user), db=Depends(get_db)):
    # Revoke database authorization before provider I/O, without blocking asyncio.
    result, needs_cleanup = await run_in_threadpool(end_state, db, u, session_id)
    if needs_cleanup:
        await terminate_room(session_id)
    elif result.get('participant_left'):
        await remove_participant(session_id,u.id)
    return result


def end_state(db, u, session_id):
    s = get_session(db, u, session_id)
    if s.event_id:
        from .events import leave
        leave(s.event_id,u,db);result={**serialize(s),'participant_left':True};db.commit();return result,s.state=='ended'
    active=conversations.members(db,s)
    if s.state=='accepted' and len(active)>2:
        conversations.leave(db,s,u.id,'left',whole_conversation=False)
        result={**serialize(s),'participant_left':True};db.commit();return result,False
    needs_cleanup=s.kind in {'voice','liveface'} and s.state in {'accepted','ended'}
    s.state='ended';s.ended_at=time.time();s.end_reason='left'
    for m in conversations.members(db,s):m.state='left';m.left_at=time.time();m.reason='left'
    result=serialize(s);db.commit();return result,needs_cleanup

async def remove_participant(id,user_id):
    if not provider_ready():return
    from livekit import api
    async with api.LiveKitAPI(os.environ['LIVEKIT_URL'],os.environ['LIVEKIT_API_KEY'],os.environ['LIVEKIT_API_SECRET']) as client:
        try:await client.room.remove_participant(api.RoomParticipantIdentity(room='pulse-'+id,identity=user_id,revoke_token_ts=int(time.time())+1))
        except api.TwirpError as e:
            if e.code!='not_found':raise



@router.post("/media/{session_id}/token")
def token(session_id: str, u=Depends(current_user), db=Depends(get_db)):
    from livekit import api

    s = get_session(db, u, session_id)
    conversations.enforce(db,s)
    own=conversations.member(db,s,u.id)
    if s.state!='accepted' or s.kind not in {'voice','liveface'} or not own or own.state!='active' or (not s.event_id and len(conversations.members(db,s))<2) or any(blocked(db,u.id,m.user_id) for m in conversations.members(db,s) if m.user_id!=u.id):
        raise HTTPException(403,'Mutual consent and active membership required')
    event=db.get(Event,s.event_id) if s.event_id else None
    attendee=db.get(Attendee,(s.event_id,u.id)) if event else None
    can_speak=not event or bool(attendee and attendee.role in ['host','cohost','speaker'])
    from .event_presentation import effective_share
    can_share=bool(event and effective_share(event,attendee))
    can_publish=can_speak or can_share
    sources=(["microphone"] if s.kind=='voice' else ["camera","microphone"]) if can_speak else []
    if can_share:sources += ['screen_share','screen_share_audio']
    if event and (event.status!='live' or not attendee or attendee.state!='active'):raise HTTPException(403,'Join the live event first')
    if not event and (not s.accepted_at or time.time() - s.accepted_at > 600):
        raise HTTPException(409, "Session allowance expired")
    if not provider_ready():
        raise HTTPException(
            503,
            "LiveKit is not configured. No camera or microphone access has been requested.",
        )
    # Room-scoped grant and short join expiry. Server maintenance revokes the room at session deadline.
    t = (
        api.AccessToken(os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"])
        .with_identity(u.id)
        .with_name(u.username)
        .with_ttl(timedelta(seconds=60))
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room="pulse-" + s.id,
                can_publish=can_publish,
                can_subscribe=True,
                can_publish_sources=sources,
                can_publish_data=False,
            )
        )
    )
    return {
        "token": t.to_jwt(),
        "url": os.environ["LIVEKIT_URL"],
        "room": "pulse-" + s.id,
        "kind": s.kind,
        "expires_at": event.ends_at if event else s.accepted_at + 600,
        "can_publish":can_publish,
        "can_speak":can_speak,
        "can_share":can_share,
    }


async def update_participant_permission(id,user_id,can_publish,kind="liveface",can_share=False):
    if not provider_ready():return
    from livekit import api
    async with api.LiveKitAPI(os.environ['LIVEKIT_URL'],os.environ['LIVEKIT_API_KEY'],os.environ['LIVEKIT_API_SECRET']) as client:
        sources=([api.TrackSource.MICROPHONE] if kind=='voice' else [api.TrackSource.MICROPHONE,api.TrackSource.CAMERA]) if can_publish else []
        if can_share:sources += [api.TrackSource.SCREEN_SHARE,api.TrackSource.SCREEN_SHARE_AUDIO]
        try:await client.room.update_participant(api.UpdateParticipantRequest(room='pulse-'+id,identity=user_id,permission=api.ParticipantPermission(can_publish=can_publish or can_share,can_subscribe=True,can_publish_data=False,can_publish_sources=sources)))
        except api.TwirpError as e:
            if e.code!='not_found':raise
