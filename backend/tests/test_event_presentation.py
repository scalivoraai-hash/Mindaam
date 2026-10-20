import time,uuid
import jwt
from fastapi import HTTPException
from backend.tests.test_core import system,register,onboard
from backend.tests.test_social_events import setup
from backend.api import event_presentation as presentation,media
from backend.api.models import Event,Attendee,Presence

def test_role_permission_commit_keeps_event_loop_responsive(system,monkeypatch):
 """A contended permission commit must not block the loop releasing its lock."""
 import asyncio,threading
 from backend.api import events
 from backend.api.models import User
 c,dbs,host,guest,_,event_id,_=live_event(system,monkeypatch)
 with dbs() as db:
  user=db.get(User,host[1]['id'])
  commit=db.commit;calls=[];released=threading.Event()
  async def scenario():
   loop=asyncio.get_running_loop()
   def contended_commit():
    calls.append(threading.get_ident())
    if len(calls)==2:
     loop.call_soon_threadsafe(released.set)
     assert released.wait(2),'Role permission commit blocked the ASGI event loop'
    commit()
   monkeypatch.setattr(db,'commit',contended_commit)
   assert await events.moderate(event_id,guest[1]['id'],'speaker',user,db)=={'ok':True}
  asyncio.run(scenario())
  assert len(calls)==2 and released.is_set()
 with dbs() as db:
  attendee=db.get(Attendee,(event_id,guest[1]['id']))
  assert attendee.role=='speaker' and attendee.permission_dirty is False

def live_event(system,monkeypatch):
 c,dbs=system;a,b,d,id=setup(c,mode='liveface')
 for who in [b,d]:assert c.post(f'/api/events/{id}/join',headers=who[0]).status_code==200
 started=c.post(f'/api/events/{id}/state/start',headers=a[0]).json()
 async def permissions(*args):pass
 async def valid(*args):return None
 monkeypatch.setattr(media,'update_participant_permission',permissions)
 monkeypatch.setattr(presentation,'provider_screen',valid)
 for key,value in [('LIVEKIT_URL','wss://test.invalid'),('LIVEKIT_API_KEY','test-key'),('LIVEKIT_API_SECRET','test-secret-at-least-32-characters')]:monkeypatch.setenv(key,value)
 return c,dbs,a,b,d,id,started['session_id']

def test_separate_screen_permission_switch_revoke_and_late_join(system,monkeypatch):
 c,dbs,a,b,d,id,sid=live_event(system,monkeypatch);base=f'/api/events/{id}/presentation'
 before=c.get('/api/world/london',headers=b[0]).json().get('position')
 assert c.post(base+'/people/'+b[1]['id']+'/allow',headers=d[0]).status_code==403
 assert c.post(base+'/start',headers=b[0],json={'request_id':str(uuid.uuid4())}).status_code==403
 assert c.post(base+'/request',headers=b[0]).status_code==200
 detail=c.get('/api/events/'+id,headers=a[0]).json();person=next(p for p in detail['participants'] if p['id']==b[1]['id'])
 assert person['share_state']=='pending' and not person['hand'] and person['role']=='audience'
 assert c.post(base+'/people/'+b[1]['id']+'/allow',headers=a[0]).status_code==200
 first=str(uuid.uuid4());assert c.post(base+'/start',headers=b[0],json={'request_id':first}).status_code==200
 grant=c.post('/api/media/'+sid+'/token',headers=b[0]).json();payload=jwt.decode(grant['token'],options={'verify_signature':False})
 assert grant['can_share'] and not grant['can_speak']
 assert set(payload['video']['canPublishSources'])=={'screen_share','screen_share_audio'}
 assert c.get('/api/events/'+id,headers=a[0]).json()['presentation']['presenter_id'] is None
 assert c.post(base+'/published',headers=b[0],json={'request_id':first,'screen_track_id':'provider-screen-B'}).status_code==200
 assert c.get('/api/media',headers=d[0]).json()[0]['presentation']['screen_track_id']=='provider-screen-B'
 # Merely approving the next person does not replace a live presentation.
 assert c.post(base+'/people/'+d[1]['id']+'/allow',headers=a[0]).status_code==200
 second=str(uuid.uuid4());assert c.post(base+'/start',headers=d[0],json={'request_id':second}).status_code==409
 assert c.post(base+'/people/'+d[1]['id']+'/switch',headers=a[0]).status_code==200
 assert c.post(base+'/start',headers=d[0],json={'request_id':second}).status_code==200
 assert c.get('/api/events/'+id,headers=a[0]).json()['presentation']['presenter_id']==b[1]['id']
 assert c.post(base+'/published',headers=d[0],json={'request_id':second,'screen_track_id':'provider-screen-D'}).status_code==200
 assert c.post(base+'/stop',headers=b[0],json={'request_id':first}).status_code==200
 assert c.get('/api/events/'+id,headers=a[0]).json()['presentation']['presenter_id']==d[1]['id']
 assert not c.post('/api/media/'+sid+'/token',headers=b[0]).json()['can_publish']
 assert c.post(base+'/people/'+d[1]['id']+'/revoke',headers=a[0]).status_code==200
 assert c.get('/api/events/'+id,headers=a[0]).json()['presentation']['presenter_id'] is None
 assert c.post(base+'/heartbeat',headers=d[0],json={'screen_track_id':'provider-screen-D'}).status_code==409
 with dbs() as db:
  assert db.get(Attendee,(id,b[1]['id'])).role=='audience'
  p=db.get(Presence,b[1]['id'])
  if before:assert (p.x,p.z)==(before['x'],before['z'])


def test_provider_rejection_picker_cancel_lease_and_scoped_stop(system,monkeypatch):
 c,dbs,a,b,d,id,sid=live_event(system,monkeypatch);base=f'/api/events/{id}/presentation';request=str(uuid.uuid4())
 assert c.post(base+'/start',headers=a[0],json={'request_id':request}).status_code==200
 async def invalid(*args):raise HTTPException(409,'Your screen is not ready yet')
 monkeypatch.setattr(presentation,'provider_screen',invalid)
 assert c.post(base+'/published',headers=a[0],json={'request_id':request,'screen_track_id':'wrong-camera-source'}).status_code==409
 assert c.post(base+'/stop',headers=a[0],json={'request_id':request}).status_code==200
 assert c.get('/api/events/'+id,headers=a[0]).json()['presentation']['pending_id'] is None
 async def valid(*args):return None
 monkeypatch.setattr(presentation,'provider_screen',valid)
 assert c.post(base+'/start',headers=a[0],json={'request_id':request}).status_code==200
 assert c.post(base+'/published',headers=a[0],json={'request_id':request,'screen_track_id':'screen1'}).status_code==200
 second=str(uuid.uuid4());assert c.post(base+'/start',headers=a[0],json={'request_id':second}).status_code==200
 assert c.post(base+'/published',headers=a[0],json={'request_id':second,'screen_track_id':'screen2'}).status_code==200
 assert c.post(base+'/stop',headers=a[0],json={'request_id':request}).status_code==200
 assert c.get('/api/events/'+id,headers=a[0]).json()['presentation']['screen_track_id']=='screen2'
 with dbs.begin() as db:
  e=db.get(Event,id);e.presentation={**e.presentation,'lease_until':time.time()-1};presentation.expire(db,e)
 assert c.get('/api/events/'+id,headers=a[0]).json()['presentation']['presenter_id'] is None


def test_lighting_authorisation_and_no_local_view_fields(system,monkeypatch):
 c,dbs,a,b,d,id,sid=live_event(system,monkeypatch)
 before=c.get('/api/events/'+id,headers=a[0]).json()['presentation']
 assert c.put('/api/events/'+id+'/lighting',headers=b[0],json={'preset':'PURPLE WAVE'}).status_code==403
 assert c.put('/api/events/'+id+'/lighting',headers=a[0],json={'preset':'PURPLE WAVE','intensity':.5}).status_code==200
 assert c.get('/api/media',headers=b[0]).json()[0]['presentation']['lighting']['preset']=='PURPLE WAVE'
 assert c.put('/api/events/'+id+'/lighting',headers=a[0],json={'preset':'PULSE','fullscreen':True}).status_code==422
 assert c.get('/api/events/'+id,headers=a[0]).json()['presentation']['revision']==before['revision']
