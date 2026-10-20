"""Membership and proximity for existing MediaSession conversations, never device GPS."""
import math
import os
import time
from fastapi import HTTPException
from sqlalchemy import select, or_
from .models import MediaSession, ConversationMember, ConversationJoin, Presence, User, Notification, Event
from .auth import display_profile


def rules():
    start=max(1,float(os.getenv('TALK_INTERACTION_METRES','10')))
    warning=max(start+1,float(os.getenv('TALK_WARNING_METRES','18')))
    disconnect=max(warning+1,float(os.getenv('TALK_DISCONNECT_METRES','25')))
    return dict(interaction_start_distance=start,interaction_warning_distance=warning,interaction_disconnect_distance=disconnect,disconnect_grace_period=max(2,float(os.getenv('TALK_DISCONNECT_GRACE_SECONDS','8'))),max_participants=max(2,min(10,int(os.getenv('TALK_MAX_PARTICIPANTS','8')))),approval_policy=os.getenv('TALK_JOIN_APPROVAL','originals'),rejoin_cooldown=max(30,int(os.getenv('TALK_REJOIN_COOLDOWN_SECONDS','120'))))


def members(db,s,include_inactive=False):
    rows=list(db.scalars(select(ConversationMember).where(ConversationMember.session_id==s.id)))
    if not rows and s.state=='accepted':
        rows=[ConversationMember(session_id=s.id,user_id=id,state='active',role='ORIGINAL_MODERATOR',joined_at=s.accepted_at or s.created_at,warning=False) for id in (s.requester,s.target)]
        db.add_all(rows);db.flush()
    return rows if include_inactive else [m for m in rows if m.state=='active']


def member(db,s,id):
    return next((m for m in members(db,s,True) if m.user_id==id),None)


def root(db,s):return db.get(MediaSession,s.conversation_id) if s.conversation_id else s

def family(db,s):
    r=root(db,s)
    return list(db.scalars(select(MediaSession).where(or_(MediaSession.id==r.id,MediaSession.conversation_id==r.id))))


def distance(a,b,now):
    if not a or not b or a.city!=b.city or a.zone_id!=b.zone_id or min(a.updated_at,b.updated_at)<now-45:return math.inf
    return math.hypot(a.x-b.x,a.z-b.z)


def end_member(db,s,m,reason,now=None):
    now=now or time.time()
    if m.state=='left':return
    m.state='left';m.left_at=now;m.reason=reason;m.warning=False;m.out_since=None
    db.add(Notification(user_id=m.user_id,kind='conversation.left',body='Connection ended — '+('moved out of range' if reason=='out_of_range' else reason.replace('_',' ')),source=s.id))
    if s.event_id:return
    remaining=members(db,s)
    if not s.conversation_id and not any(p.user_id in [s.requester,s.target] for p in remaining):
        for item in family(db,s):
            item.state='ended';item.ended_at=now;item.end_reason='moderators_left'
            for p in members(db,item):p.state='left';p.left_at=now;p.reason='moderators_left';p.warning=False
        return
    if len(remaining)<2:
        s.state='ended';s.ended_at=now;s.end_reason=reason
        for other in remaining:other.state='left';other.left_at=now;other.reason=reason;other.warning=False


def leave(db,s,id,reason='left',whole_conversation=True):
    for item in family(db,s) if whole_conversation else [s]:
        m=member(db,item,id)
        if m:end_member(db,item,m,reason)


def enforce(db,s,now=None):
    """Two-second maintenance sampling plus grant-time validation; no frame polling."""
    if s.state!='accepted':return
    now=now or time.time();cfg=rules();active=members(db,s)
    if s.event_id:
        from .models import Event,Attendee
        from .world import blocked
        event=db.get(Event,s.event_id)
        if not event or event.status!='live':
            s.state='ended';s.ended_at=now;s.end_reason='event_ended';return
        for m in active:
            person=db.get(User,m.user_id);a=db.get(Attendee,(event.id,m.user_id))
            if not a or a.state!='active' or not person or person.suspended:
                end_member(db,s,m,'event_left',now)
        return
    invited=[m for m in members(db,s,True) if m.state=='invited']
    if len(active)<2 and invited and now-s.created_at<30:return
    from .world import blocked
    positions={m.user_id:db.get(Presence,m.user_id) for m in active}
    for m in active:
        if m.state!='active':continue
        u=db.get(User,m.user_id)
        if not u or u.suspended:
            end_member(db,s,m,'account_unavailable',now);continue
        if any(blocked(db,m.user_id,other.user_id) for other in active if other.user_id!=m.user_id and other.state=='active'):
            # Fail closed: the blocking member leaves; others cannot communicate with them.
            end_member(db,s,m,'privacy_changed',now);continue
        if s.distance_policy=='friends' and len(active)==2:
            from .world import friends
            other=next((o for o in active if o.user_id!=m.user_id),None)
            if other and friends(db,m.user_id,other.user_id):
                m.warning=False;m.out_since=None;continue
        d=min((distance(positions[m.user_id],positions[o.user_id],now) for o in active if o.user_id!=m.user_id and o.state=='active'),default=math.inf)
        m.warning=d>cfg['interaction_warning_distance']
        if d<=cfg['interaction_warning_distance']:m.out_since=None
        elif d>cfg['interaction_disconnect_distance']:
            m.out_since=m.out_since or now
            if now-m.out_since>=cfg['disconnect_grace_period']:end_member(db,s,m,'out_of_range',now)


def view(db,s,u):
    from .core import serialize
    rows=members(db,s);own=member(db,s,u.id)
    state='pending' if own and own.state=='invited' else 'ended' if own and own.state=='left' else s.state
    return {**serialize(s),'state':state,'revision':max(s.created_at,s.accepted_at or 0,s.ended_at or 0,own.joined_at if own else 0,own.left_at or 0 if own else 0),'members':[{'id':p.id,'username':p.username,'avatar':p.avatar,'role':m.role,**display_profile(p)} for m in rows if (p:=db.get(User,m.user_id))], 'capacity':min(s.max_participants,rules()['max_participants']),'hard_maximum':rules()['max_participants'],'proximity_warning':bool(own and own.warning),'end_reason':own.reason if own and own.reason else s.end_reason,'root_id':s.conversation_id or s.id,'event_title':db.get(Event,s.event_id).title if s.event_id else None,'join_policy':s.join_policy,'group':len(rows)>2,'invited':bool(own and own.state=='invited')}


def eligible(db,s,u):
    from .world import blocked,friends
    from .talk import preferences
    if s.state!='accepted' or s.join_policy not in ['approval','friends']:return False
    active=members(db,s)
    own=member(db,s,u.id)
    if own and own.rejoin_after and own.rejoin_after>time.time():return False
    if not active or any(m.user_id==u.id for m in active) or len(active)>=min(s.max_participants,rules()['max_participants']):return False
    now=time.time();position=db.get(Presence,u.id)
    for m in active:
        p=db.get(User,m.user_id)
        if not p or p.suspended or blocked(db,u.id,p.id) or p.privacy in ['Ghost Mode','Event Mode'] or (p.privacy=='Friends Only' and not friends(db,u.id,p.id)):return False
        policy=preferences(db,p.id)['text']
        if policy=='nobody' or policy=='connections' and not friends(db,u.id,p.id):return False
        if policy=='following':
            from .models import Social
            if not friends(db,u.id,p.id) and not db.scalar(select(Social.id).where(Social.actor==p.id,Social.target==u.id,Social.kind=='follow')):return False
        from .models import Social
        if db.scalar(select(Social.id).where(Social.actor==p.id,Social.target==u.id,Social.kind=='mute')):return False
        if s.join_policy=='friends' and not friends(db,u.id,p.id):return False
    return any(distance(position,db.get(Presence,m.user_id),now)<=rules()['interaction_start_distance'] for m in active)


def nearby_conversations(db,u):
    # Restrict candidate roots to conversations of visible nearby presence.
    pos=db.get(Presence,u.id)
    if not pos:return []
    radius=rules()['interaction_start_distance']
    ids=list(db.scalars(select(Presence.user_id).where(Presence.city==pos.city,Presence.updated_at>time.time()-45,Presence.x.between(pos.x-radius,pos.x+radius),Presence.z.between(pos.z-radius,pos.z+radius))))
    roots=db.scalars(select(MediaSession).where(MediaSession.state=='accepted',MediaSession.conversation_id==None,MediaSession.event_id==None,or_(MediaSession.requester.in_(ids),MediaSession.target.in_(ids),MediaSession.id.in_(select(ConversationMember.session_id).where(ConversationMember.user_id.in_(ids),ConversationMember.state=='active')))).limit(30))
    result=[]
    for s in roots:
        if not eligible(db,s,u):continue
        rows=members(db,s);request=db.get(ConversationJoin,(s.id,u.id))
        result.append({'id':s.id,'kind':s.kind,'capacity':min(s.max_participants,rules()['max_participants']),'count':len(rows),'names':[db.get(User,m.user_id).username for m in rows],'request_state':request.state if request and request.created_at>time.time()-30 else None})
    return result


def cleanup_participants(db):
    now=time.time()
    return [(m.session_id,m.user_id) for m in db.scalars(select(ConversationMember).where(ConversationMember.state=='left',ConversationMember.left_at>now-660)) if (s:=db.get(MediaSession,m.session_id)) and s.kind!='text' and s.state=='accepted']
