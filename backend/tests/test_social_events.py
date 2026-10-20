import time,uuid
from sqlalchemy import select
from backend.tests.test_core import system,register,onboard
from backend.api.models import Event,Attendee,MediaSession,Presence,Session,ConversationMember
from backend.api import events,conversations

def setup(c,visibility='public',mode='voice',kind='Public Talk'):
 a=register(c,'event_host');b=register(c,'event_guest');d=register(c,'event_other')
 for h,u in [a,b,d]:onboard(c,h)
 r=c.post('/api/events',headers=a[0],json={'title':'Real event API regression','description':'Test database only','city':'manchester','starts_at':time.time()+300,'capacity':6,'visibility':visibility,'communication_mode':mode,'event_type':kind})
 assert r.status_code==201,r.text
 return a,b,d,r.json()['id']

def test_public_event_stage_permissions_and_cleanup(system,monkeypatch):
 c,dbs=system;a,b,d,id=setup(c)
 assert c.post(f'/api/events/{id}/state/start',headers=b[0]).status_code==403
 assert c.post(f'/api/events/{id}/join',headers=b[0]).status_code==200
 assert c.post(f'/api/events/{id}/join',headers=b[0]).json()['attendees']==2
 live=c.post(f'/api/events/{id}/state/start',headers=a[0]);assert live.status_code==200,live.text
 sid=live.json()['session_id'];assert c.post(f'/api/events/{id}/hand',headers=b[0]).json()['raised']
 from backend.api import media
 async def permission(*args):pass
 monkeypatch.setattr(media,'update_participant_permission',permission)
 for key,value in [('LIVEKIT_URL','wss://test.invalid'),('LIVEKIT_API_KEY','test-key'),('LIVEKIT_API_SECRET','test-secret-at-least-32-characters')]:monkeypatch.setenv(key,value)
 grant=c.post(f'/api/media/{sid}/token',headers=b[0]);assert grant.status_code==200,grant.text;assert grant.json()['can_publish']==False
 assert c.post(f'/api/events/{id}/people/{b[1]["id"]}/speaker',headers=d[0]).status_code==403
 assert c.post(f'/api/events/{id}/people/{b[1]["id"]}/speaker',headers=a[0]).status_code==200
 assert c.post(f'/api/media/{sid}/token',headers=b[0]).json()['can_publish']==True
 assert c.post(f'/api/events/{id}/people/{b[1]["id"]}/audience',headers=a[0]).status_code==200
 assert c.post(f'/api/media/{sid}/token',headers=b[0]).json()['can_publish']==False
 assert c.post(f'/api/events/{id}/people/{a[1]["id"]}/remove',headers=a[0]).status_code==403
 assert c.post(f'/api/events/{id}/state/end',headers=a[0]).status_code==200
 assert c.post(f'/api/media/{sid}/token',headers=b[0]).status_code==403
 with dbs() as db:assert db.get(MediaSession,sid).state=='ended'

def test_private_event_invite_request_approval_remove(system,monkeypatch):
 c,dbs=system;a,b,d,id=setup(c,'private','liveface','Video Meetup')
 assert c.get(f'/api/events/{id}',headers=b[0]).status_code==404
 assert not c.get('/api/events?city=manchester',headers=b[0]).json()
 assert c.post(f'/api/events/{id}/invite',headers=a[0],json={'user_id':b[1]['id']}).status_code==200
 assert c.post(f'/api/events/{id}/join',headers=b[0]).json()['my_state']=='pending'
 assert c.post(f'/api/events/{id}/people/{b[1]["id"]}/approve',headers=d[0]).status_code==404
 assert c.post(f'/api/events/{id}/people/{b[1]["id"]}/approve',headers=a[0]).status_code==200
 assert c.post(f'/api/events/{id}/people/{b[1]["id"]}/approve',headers=a[0]).status_code==200
 live=c.post(f'/api/events/{id}/state/start',headers=a[0]).json();sid=live['session_id']
 assert not c.get(f'/api/events/{id}',headers=a[0]).json()['requests']
 from backend.api import media
 async def remove(*args):pass
 monkeypatch.setattr(media,'remove_participant',remove)
 assert c.post(f'/api/events/{id}/people/{b[1]["id"]}/remove',headers=a[0]).status_code==200
 assert c.post(f'/api/events/{id}/join',headers=b[0]).status_code==403
 assert c.post(f'/api/media/{sid}/token',headers=b[0]).status_code==403
 with dbs() as db:assert db.get(Presence,b[1]['id']) is not None

def test_event_text_and_cancellation(system):
 c,dbs=system;a,b,d,id=setup(c,mode='text',kind='Discussion')
 c.post(f'/api/events/{id}/join',headers=b[0]);live=c.post(f'/api/events/{id}/state/start',headers=a[0]).json();sid=live['session_id']
 assert c.post(f'/api/talk/{sid}/messages',headers=b[0],json={'id':str(uuid.uuid4()),'body':'Event text'}).status_code==201
 state=next(s for s in c.get('/api/talk/state',headers=a[0]).json() if s['id']==sid)
 assert state['messages'][-1]['body']=='Event text'
 c.post(f'/api/events/{id}/leave',headers=b[0])
 with dbs() as db:assert db.get(MediaSession,sid).state=='accepted'
 assert c.post(f'/api/events/{id}/state/cancel',headers=a[0]).status_code==200
 assert c.post(f'/api/events/{id}/join',headers=d[0]).status_code==409

def test_real_city_counts_transfer_timeout_and_session_expiry(system):
 c,dbs=system;a=register(c,'count_one');b=register(c,'count_two')
 for h,u in [a,b]:onboard(c,h);c.post('/api/growth/worlds/milton-keynes/starter',headers=h,json={'confirmed':True});c.post('/api/world/enter',headers=h,json={'city':'milton-keynes'})
 def counts():return {x['id']:x['online'] for x in c.get('/api/cities').json()}
 assert counts()['milton-keynes']==2 and counts()['manchester']==0
 assert c.post('/api/growth/worlds/manchester/starter',headers=b[0],json={'confirmed':True}).status_code==200
 c.post('/api/world/enter',headers=b[0],json={'city':'manchester'})
 assert counts()['milton-keynes']==1 and counts()['manchester']==1
 with dbs.begin() as db:db.get(Presence,b[1]['id']).updated_at=time.time()-46
 assert counts()['manchester']==0
 with dbs.begin() as db:
  for s in db.scalars(select(Session).where(Session.user_id==a[1]['id'])):s.expires_at=time.time()-1
 assert counts()['milton-keynes']==0

