import time,uuid
from sqlalchemy import select
from backend.tests.test_core import system,register,onboard
from backend.api.models import MediaSession,ConversationMember,ConversationJoin,Presence
from backend.api import conversations

def group_setup(c):
    users=[]
    for name in ['group_alice','group_bob','group_cora']:
        h,u=register(c,name);onboard(c,h);users.append((h,u))
    a,b,d=users
    sid=c.post('/api/talk/request',headers=a[0],json={'target_id':b[1]['id'],'kind':'text'}).json()['id']
    assert c.post(f'/api/talk/{sid}/accept',headers=b[0]).status_code==200
    return users,sid

def join(c,sid,member,guest):
    assert c.post(f'/api/talk/conversation/{sid}/join',headers=guest[0]).status_code==200
    return c.post(f'/api/talk/conversation/{sid}/join/{guest[1]["id"]}/accept',headers=member[0])

def test_group_approval_idempotency_messages_and_same_media_room(system,monkeypatch):
    c,dbs=system;users,sid=group_setup(c);a,b,d=users
    assert c.post(f'/api/talk/{sid}/messages',headers=d[0],json={'id':str(uuid.uuid4()),'body':'unauthorised'}).status_code==403
    call=c.post('/api/media/request',headers=a[0],json={'target_id':b[1]['id'],'kind':'liveface'}).json()['id']
    assert c.post(f'/api/media/{call}/accept',headers=b[0]).status_code==200
    near=c.get('/api/talk/nearby-conversations',headers=d[0]).json()
    assert any(x['id']==sid and 'messages' not in x for x in near)
    assert join(c,sid,a,d).status_code==200
    assert c.post(f'/api/talk/conversation/{sid}/join/{d[1]["id"]}/accept',headers=b[0]).status_code==200
    with dbs() as db:
        assert len(conversations.members(db,db.get(MediaSession,sid)))==3
        assert len(conversations.members(db,db.get(MediaSession,call)))==3
    message={'id':str(uuid.uuid4()),'body':'Group regression message'}
    assert c.post(f'/api/talk/{sid}/messages',headers=d[0],json=message).status_code==201
    for h,u in [a,b]:
        state=next(s for s in c.get('/api/talk/state',headers=h).json() if s['id']==sid)
        assert state['messages'][-1]['body']==message['body']
        assert state['messages'][-1]['sender_name']==d[1]['username']
        assert not state['join_requests']
    for key,value in [('LIVEKIT_URL','wss://test.invalid'),('LIVEKIT_API_KEY','test-key'),('LIVEKIT_API_SECRET','test-secret-at-least-32-characters')]:monkeypatch.setenv(key,value)
    grants=[c.post(f'/api/media/{call}/token',headers=h).json() for h,u in users]
    assert all(g['room']=='pulse-'+call for g in grants)
    assert all(g['kind']=='liveface' for g in grants)

def test_independent_proximity_grace_hysteresis_and_cleanup(system):
    c,dbs=system;users,sid=group_setup(c);a,b,d=users
    assert join(c,sid,b,d).status_code==200
    with dbs.begin() as db:
        now=time.time();s=db.get(MediaSession,sid);p=db.get(Presence,d[1]['id']);p.x=20;p.z=0;p.updated_at=now
        conversations.enforce(db,s,now);m=conversations.member(db,s,d[1]['id']);assert m.warning and m.out_since is None
        p.x=30;conversations.enforce(db,s,now+1);assert m.state=='active' and m.out_since==now+1
        p.x=23;conversations.enforce(db,s,now+4);assert m.state=='active' and m.out_since==now+1
        p.x=10;conversations.enforce(db,s,now+5);assert m.out_since is None
        p.x=35;conversations.enforce(db,s,now+6);conversations.enforce(db,s,now+15)
        assert m.state=='left' and m.reason=='out_of_range'
        assert s.state=='accepted' and len(conversations.members(db,s))==2
    assert c.post(f'/api/talk/{sid}/messages',headers=d[0],json={'id':str(uuid.uuid4()),'body':'after leave'}).status_code==403
    assert c.post(f'/api/talk/{sid}/messages',headers=a[0],json={'id':str(uuid.uuid4()),'body':'pair continues'}).status_code==201

def test_capacity_blocking_closed_policy_and_expired_join(system,monkeypatch):
    c,dbs=system;users,sid=group_setup(c);a,b,d=users
    assert c.put(f'/api/talk/conversation/{sid}/policy',headers=a[0],json={'policy':'closed'}).status_code==200
    assert c.post(f'/api/talk/conversation/{sid}/join',headers=d[0]).status_code==403
    c.put(f'/api/talk/conversation/{sid}/policy',headers=a[0],json={'policy':'approval'})
    assert join(c,sid,a,d).status_code==200
    monkeypatch.setenv('TALK_MAX_PARTICIPANTS','4')
    e=(register(c,'group_dan'));onboard(c,e[0]);assert join(c,sid,b,e).status_code==200
    f=register(c,'group_erin');onboard(c,f[0]);assert c.post(f'/api/talk/conversation/{sid}/join',headers=f[0]).status_code==403
    assert c.post('/api/social/'+d[1]['id']+'/block',headers=a[0]).status_code==200
    assert c.post(f'/api/talk/{sid}/messages',headers=a[0],json={'id':str(uuid.uuid4()),'body':'blocked path'}).status_code==403
    assert c.post(f'/api/talk/{sid}/messages',headers=b[0],json={'id':str(uuid.uuid4()),'body':'remaining group'}).status_code==201

def test_group_media_requires_each_invitee_consent(system):
    c,dbs=system;users,sid=group_setup(c);a,b,d=users;assert join(c,sid,a,d).status_code==200
    call=c.post(f'/api/talk/conversation/{sid}/media/voice',headers=a[0]).json()['id']
    assert c.post(f'/api/media/{call}/token',headers=d[0]).status_code==403
    assert c.post(f'/api/media/{call}/accept',headers=d[0]).status_code==200
    assert c.post(f'/api/media/{call}/token',headers=d[0]).status_code==503
    assert c.post(f'/api/media/{call}/reject',headers=b[0]).status_code==200
    assert c.post(f'/api/media/{call}/token',headers=b[0]).status_code==403

def test_default_six_capacity_and_departed_founder_discovery(system):
    c,dbs=system;users,sid=group_setup(c);a,b,d=users
    assert join(c,sid,a,d).status_code==200
    for name in ['four','five','six']:
        guest=register(c,'capacity_'+name);onboard(c,guest[0]);assert join(c,sid,b,guest).status_code==200
    guest=register(c,'capacity_seven');onboard(c,guest[0])
    assert c.post(f'/api/talk/conversation/{sid}/join',headers=guest[0]).status_code==403
    assert c.post(f'/api/talk/{sid}/end',headers=a[0]).status_code==200
    with dbs.begin() as db:
        for _,user in [a,b]:db.get(Presence,user['id']).x=500
    assert any(s['id']==sid and s['count']==5 for s in c.get('/api/talk/nearby-conversations',headers=guest[0]).json())
    assert join(c,sid,b,guest).status_code==200
    assert c.post(f'/api/talk/conversation/{sid}/join',headers=guest[0]).status_code==200

def test_join_cancel_expiry_and_blocked_pending(system):
    c,dbs=system;users,sid=group_setup(c);a,b,d=users;path=f'/api/talk/conversation/{sid}/join'
    assert c.post(path,headers=d[0]).status_code==200
    assert c.post(path+'/'+d[1]['id']+'/cancel',headers=d[0]).json()['state']=='cancelled'
    with dbs.begin() as db:db.get(ConversationJoin,(sid,d[1]['id'])).created_at-=40
    c.post(path,headers=d[0])
    with dbs.begin() as db:db.get(ConversationJoin,(sid,d[1]['id'])).created_at-=40
    assert c.post(path+'/'+d[1]['id']+'/accept',headers=a[0]).status_code==409
    c.get('/api/talk/state',headers=a[0])
    with dbs() as db:assert db.get(ConversationJoin,(sid,d[1]['id'])).state=='expired'
    c.post(path,headers=d[0])
    assert c.post('/api/social/'+d[1]['id']+'/block',headers=a[0]).status_code==200
    with dbs() as db:assert db.get(ConversationJoin,(sid,d[1]['id'])).state=='blocked'
    assert c.post(path+'/'+d[1]['id']+'/accept',headers=b[0]).status_code==409

def test_pair_disconnect_ends_every_media_kind_and_denies_grants(system):
    c,dbs=system;users,sid=group_setup(c);a,b,_=users;ids=[sid]
    for kind in ['voice','liveface']:
        call=c.post('/api/media/request',headers=a[0],json={'target_id':b[1]['id'],'kind':kind}).json()['id']
        assert c.post('/api/media/'+call+'/accept',headers=b[0]).status_code==200;ids.append(call)
    with dbs.begin() as db:
        now=time.time();p=db.get(Presence,b[1]['id']);p.x=50;p.z=0
        for id in ids:
            s=db.get(MediaSession,id);conversations.enforce(db,s,now);assert s.state=='accepted'
            conversations.enforce(db,s,now+9);assert s.state=='ended' and s.end_reason=='out_of_range'
    for id in ids[1:]:assert c.post('/api/media/'+id+'/token',headers=a[0]).status_code==403
    assert not c.get('/api/media',headers=a[0]).json()


def test_original_moderators_remove_guest_and_end_when_both_leave(system):
    c,dbs=system;users,sid=group_setup(c);a,b,d=users
    assert join(c,sid,a,d).status_code==200
    e=register(c,'moderation_four');onboard(c,e[0])
    assert c.post(f'/api/talk/conversation/{sid}/join',headers=e[0]).status_code==200
    assert c.post(f'/api/talk/conversation/{sid}/join/{e[1]["id"]}/accept',headers=d[0]).status_code==403
    assert c.post(f'/api/talk/conversation/{sid}/join/{e[1]["id"]}/accept',headers=b[0]).status_code==200
    path=f'/api/talk/conversation/{sid}/members/'
    assert c.post(path+b[1]['id']+'/remove',headers=a[0]).status_code==403
    assert c.post(path+e[1]['id']+'/remove',headers=d[0]).status_code==403
    assert c.post(path+d[1]['id']+'/remove',headers=a[0]).status_code==200
    assert c.post(f'/api/talk/conversation/{sid}/join',headers=d[0]).status_code==403
    assert c.get('/api/world/london',headers=d[0]).status_code==200
    assert c.post(f'/api/talk/{sid}/end',headers=a[0]).status_code==200
    assert c.post(f'/api/talk/{sid}/end',headers=b[0]).status_code==200
    with dbs() as db:assert db.get(MediaSession,sid).state=='ended'
