from .auth import display_profile
import time
import asyncio
from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select, or_, and_, func, delete
from .db import get_db
from .models import *
from .auth import current_user
from .core import Strict, serialize, notify, emit, check_city
from .world import blocked, friends

router = APIRouter(prefix="/api")


def target_user(db, u, user_id):
    p = db.get(User, user_id)
    if not p or p.suspended or p.id == u.id:
        raise HTTPException(404, "Player unavailable")
    return p


@router.get("/people")
def people(u=Depends(current_user), db=Depends(get_db)):
    results = []
    for p in db.scalars(
        select(User)
        .where(User.id != u.id, User.suspended == False, User.onboarded == True)
        .limit(200)
    ):
        if blocked(db, u.id, p.id) or p.privacy in {"Ghost Mode", "Event Mode"}:
            continue
        if p.privacy == "Friends Only" and not friends(db, u.id, p.id):
            continue
        outgoing = db.scalars(
            select(Social.kind).where(Social.actor == u.id, Social.target == p.id)
        ).all()
        incoming = db.scalars(
            select(Social.kind).where(Social.actor == p.id, Social.target == u.id)
        ).all()
        presence = db.get(Presence, p.id)
        results.append(
            {
                "id": p.id,
                "username": p.username,
                "avatar": p.avatar,
                **display_profile(p),
                "city": p.city,
                "friend": friends(db, u.id, p.id),
                "following": "follow" in outgoing,
                "requested": "request" in outgoing,
                "incoming": "request" in incoming,
                "online": bool(presence and presence.updated_at > time.time() - 45),
            }
        )
    return results


@router.post("/social/{user_id}/{action}")
async def social_action(user_id: str, action: str, u=Depends(current_user), db=Depends(get_db)):
    result = await run_in_threadpool(social_action_sync, user_id, action, u, db)
    from .media import terminate_room
    rooms = result.pop('_rooms', [])
    if rooms:
        cleanup = await asyncio.gather(*(asyncio.wait_for(terminate_room(id), timeout=5) for id in rooms), return_exceptions=True)
        if any(isinstance(x, BaseException) for x in cleanup):
            result['media_cleanup_retrying'] = True
    return result

def social_action_sync(user_id, action, u, db):
    rooms = []
    list(db.scalars(select(User).where(User.id.in_([u.id,user_id])).order_by(User.id).with_for_update()))
    p = target_user(db, u, user_id)
    if action not in {"wave", "follow", "friend", "accept", "decline", "cancel", "remove", "block", "unblock", "mute"}:
        raise HTTPException(422, "Unknown social action")
    if action == "unblock":
        db.execute(
            delete(Social).where(
                Social.actor == u.id, Social.target == p.id, Social.kind == "block"
            )
        )
        return {"ok": True}
    if action != "block" and blocked(db, u.id, p.id):
        raise HTTPException(403, "Interaction unavailable")
    if action in {"decline","cancel","remove"}:
        if action=="remove":
            db.execute(delete(Social).where(Social.kind.in_(['friend','request']),or_(and_(Social.actor==u.id,Social.target==p.id),and_(Social.actor==p.id,Social.target==u.id))))
        else:
            actor,target=(p.id,u.id) if action=='decline' else (u.id,p.id)
            db.execute(delete(Social).where(Social.actor==actor,Social.target==target,Social.kind=='request'))
        db.add(Audit(actor_id=u.id,action='friend.'+action,target=p.id));return {'ok':True,'state':{'decline':'DECLINED','cancel':'CANCELLED','remove':'REMOVED'}[action]}
    if action=='friend':
        if friends(db,u.id,p.id):return {'ok':True,'state':'ACCEPTED'}
        if db.scalar(select(Social.id).where(Social.actor==u.id,Social.target==p.id,Social.kind=='request')):return {'ok':True,'state':'PENDING'}
        if db.scalar(select(func.count()).select_from(Audit).where(Audit.actor_id==u.id,Audit.action=='friend.request',Audit.created_at>time.time()-60))>=5:raise HTTPException(429,'Wait before sending more friend requests')
        db.add(Audit(actor_id=u.id,action='friend.request',target=p.id))
    if action=='accept' and friends(db,u.id,p.id):return {'ok':True,'state':'ACCEPTED'}
    if action == "wave":
        notify(db, p.id, "wave", u.username + " waved at you", u.id)
        emit(db, u, "wave_sent", p.id)
        return {"ok": True}
    kind = {"friend": "request", "accept": "friend"}.get(action, action)
    if action == "accept":
        request = db.scalar(
            select(Social).where(
                Social.actor == p.id, Social.target == u.id, Social.kind == "request"
            )
        )
        if not request:
            raise HTTPException(409, "No incoming request")
        db.execute(delete(Social).where(Social.kind=='request',or_(and_(Social.actor==u.id,Social.target==p.id),and_(Social.actor==p.id,Social.target==u.id))))
        if not friends(db, p.id, u.id):
            db.add(Social(actor=p.id, target=u.id, kind="friend"))
    if not db.scalar(
        select(Social).where(
            Social.actor == u.id, Social.target == p.id, Social.kind == kind
        )
    ):
        db.add(Social(actor=u.id, target=p.id, kind=kind))
    if action == "block":
        db.execute(delete(Social).where(Social.kind.in_(['friend','request']),or_(and_(Social.actor==u.id,Social.target==p.id),and_(Social.actor==p.id,Social.target==u.id))))
        from . import conversations
        from .models import ConversationJoin
        for j in db.scalars(select(ConversationJoin).where(ConversationJoin.state=='pending')):
            session=db.get(MediaSession,j.session_id)
            ids={m.user_id for m in conversations.members(db,session)} if session else set()
            if (j.user_id==p.id and u.id in ids) or (j.user_id==u.id and p.id in ids):j.state='blocked';j.decided_by=u.id
        for s in db.scalars(select(MediaSession).where(MediaSession.state.in_(['pending','accepted']))):
            ids={m.user_id for m in conversations.members(db,s)} if s.state=='accepted' else {s.requester,s.target}
            if u.id not in ids or p.id not in ids:continue
            if s.event_id:
                from .events import finish
                e=db.get(Event,s.event_id);removed=p.id if e and e.host_id==u.id else u.id
                a=db.get(Attendee,(s.event_id,removed))
                if a:a.state='banned' if removed==p.id else 'left';a.hand=False
                m=conversations.member(db,s,removed)
                if m:conversations.end_member(db,s,m,'blocked')
                continue
            if len(ids)>2:
                conversations.leave(db,s,u.id,'blocked',whole_conversation=False)
            else:
                if s.kind!='text':rooms.append(s.id)
                s.state='ended';s.ended_at=time.time();s.end_reason='blocked'
                for m in conversations.members(db,s):m.state='left';m.left_at=time.time();m.reason='blocked'
        db.add(Audit(actor_id=u.id, action="social.block", target=p.id))
    else:
        notify(db, p.id, action, u.username + " sent a " + action, u.id)
    db.commit()
    return {"ok": True, "_rooms": rooms}


class MessageInput(Strict):
    body: str = Field(min_length=1, max_length=2000)


@router.get("/messages/{user_id}")
def messages(user_id: str, u=Depends(current_user), db=Depends(get_db)):
    target_user(db, u, user_id)
    if blocked(db, u.id, user_id):
        raise HTTPException(403, "Conversation unavailable")
    rows = db.scalars(
        select(Message)
        .where(
            or_(
                and_(Message.sender == u.id, Message.recipient == user_id),
                and_(Message.sender == user_id, Message.recipient == u.id),
            )
        )
        .order_by(Message.created_at.desc())
        .limit(100)
    ).all()
    for m in rows:
        if m.recipient == u.id:
            m.read = True
    return [serialize(m) for m in reversed(rows)]


@router.post("/messages/{user_id}", status_code=201)
def send_message(
    user_id: str, data: MessageInput, u=Depends(current_user), db=Depends(get_db)
):
    target_user(db, u, user_id)
    if blocked(db, u.id, user_id):
        raise HTTPException(403, "Conversation unavailable")
    consent=db.scalar(select(MediaSession.id).where(or_(and_(MediaSession.requester==u.id,MediaSession.target==user_id),and_(MediaSession.requester==user_id,MediaSession.target==u.id)),MediaSession.state=='accepted'))
    from .talk import preferences
    if preferences(db,user_id)['text']=='nobody' or (not consent and not friends(db,u.id,user_id)):
        raise HTTPException(403,'Ask to talk and wait for acceptance first')
    if not data.body.strip():
        raise HTTPException(422, "Message cannot be empty")
    m = Message(sender=u.id, recipient=user_id, body=data.body.strip())
    db.add(m)
    db.flush()
    emit(db, u, "message_sent", m.id)
    notify(db, user_id, "message", u.username + " sent a message", u.id)
    return serialize(m)


class CrewInput(Strict):
    name: str = Field(min_length=3, max_length=80)
    description: str = Field(default="", max_length=500)
    city: str = "london"
    private: bool = False


@router.get("/crews")
def crews(u=Depends(current_user), db=Depends(get_db)):
    rows = []
    for c in db.scalars(select(Crew).limit(100)):
        joined = db.get(CrewMember, (c.id, u.id)) is not None
        if (c.private and not joined) or blocked(db, u.id, c.owner_id):
            continue
        rows.append(
            {
                **serialize(c),
                "joined": joined,
                "members": db.scalar(
                    select(func.count())
                    .select_from(CrewMember)
                    .where(CrewMember.crew_id == c.id)
                ),
            }
        )
    return rows


@router.post("/crews", status_code=201)
def create_crew(data: CrewInput, u=Depends(current_user), db=Depends(get_db)):
    check_city(data.city)
    if db.scalar(select(Crew.id).where(Crew.name == data.name)):
        raise HTTPException(409, "Crew name taken")
    c = Crew(**data.model_dump(), owner_id=u.id)
    db.add(c)
    db.flush()
    db.add(CrewMember(crew_id=c.id, user_id=u.id, role="owner"))
    return serialize(c)


@router.post("/crews/{crew_id}/join")
def join_crew(crew_id: str, u=Depends(current_user), db=Depends(get_db)):
    c = db.scalar(select(Crew).where(Crew.id == crew_id).with_for_update())
    if not c or c.private or blocked(db, u.id, c.owner_id):
        raise HTTPException(404, "Open Crew not found")
    if not db.get(CrewMember, (crew_id, u.id)):
        db.add(CrewMember(crew_id=crew_id, user_id=u.id))
        emit(db, u, "crew_joined", crew_id)
    return {"ok": True}


class ReportInput(Strict):
    target_id: str
    category: str = Field(min_length=3, max_length=40)
    details: str = Field(min_length=5, max_length=2000)


@router.post("/reports", status_code=201)
def report(data: ReportInput, u=Depends(current_user), db=Depends(get_db)):
    target_user(db, u, data.target_id)
    r = Report(**data.model_dump(), reporter_id=u.id)
    db.add(r)
    db.flush()
    return {"id": r.id, "status": r.status}

@router.get('/friends')
def friend_list(u=Depends(current_user),db=Depends(get_db)):
 relations=list(db.scalars(select(Social).where(or_(Social.actor==u.id,Social.target==u.id),Social.kind.in_(['friend','request']))))
 ids={r.target if r.actor==u.id else r.actor for r in relations};result=[]
 for id in ids:
  p=db.get(User,id)
  if not p or p.suspended or blocked(db,u.id,id):continue
  is_friend=friends(db,u.id,id);presence=db.get(Presence,id)
  alive=bool(presence and presence.updated_at>time.time()-45 and db.scalar(select(Session.id).where(Session.user_id==id,Session.expires_at>time.time()).limit(1)))
  hidden=p.privacy in ['Ghost Mode','Event Mode']
  pair=or_(and_(Message.sender==u.id,Message.recipient==id),and_(Message.sender==id,Message.recipient==u.id))
  latest=db.scalar(select(Message).where(pair).order_by(Message.created_at.desc()).limit(1)) if is_friend else None
  result.append({'id':id,'username':p.username,'avatar':p.avatar,'friend':is_friend,'incoming':any(r.actor==id and r.kind=='request' for r in relations),'requested':any(r.actor==u.id and r.target==id and r.kind=='request' for r in relations),'online':alive and not hidden,'city':presence.city if alive and not hidden else None,'latest':latest.body if latest else None,'unread':db.scalar(select(func.count()).select_from(Message).where(Message.sender==id,Message.recipient==u.id,Message.read==False)) if is_friend else 0})
 return result
