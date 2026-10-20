import time,uuid
from backend.tests.test_core import system,register,onboard
from backend.api.models import MediaSession,Presence

def pair(system):
 c,db=system;a,ua=register(c,'talkalice');b,ub=register(c,'talkbob')
 for h in [a,b]:onboard(c,h);c.post('/api/world/enter',headers=h,json={'city':'milton-keynes'})
 return c,db,a,ua,b,ub

def test_two_user_socket_request_accept_messages(system):
 c,db,a,ua,b,ub=pair(system)
 with c.websocket_connect('/api/realtime') as wa,c.websocket_connect('/api/realtime') as wb:
  wa.send_json({'token':a['Authorization'][7:]});wb.send_json({'token':b['Authorization'][7:]})
  assert any(p['id']==ub['id'] for p in wa.receive_json()['players'])
  assert any(p['id']==ua['id'] for p in wb.receive_json()['players'])
  r=c.post('/api/talk/request',headers=a,json={'target_id':ub['id'],'kind':'text'});assert r.status_code==200,r.text
  id=r.json()['id']
  for _ in range(5):
   if any(s['id']==id for s in wb.receive_json()['talk']):break
  else:assert False,'Recipient did not receive invitation'
  assert c.post('/api/talk/'+id+'/accept',headers=a,json={}).status_code==403
  assert c.post('/api/talk/'+id+'/accept',headers=b,json={}).status_code==200
  for h,body,ws in [(a,'Hello',wb),(b,'Hi',wa)]:
   r=c.post('/api/talk/'+id+'/messages',headers=h,json={'id':str(uuid.uuid4()),'body':body});assert r.status_code==201,r.text
   for _ in range(10):
    s=next((s for s in ws.receive_json()['talk'] if s['id']==id),{})
    if any(m['body']==body for m in s.get('messages',[])):break
   else:assert False,'Message was not delivered on socket'
  c.put('/api/talk/'+id+'/cursor',headers=b,json={'typing':True,'read':True})
  state=c.get('/api/talk/state',headers=a).json()[0];assert state['typing'] and state['messages'][0]['read']

def test_decline_cooldown_timeout(system):
 c,db,a,ua,b,ub=pair(system);id=c.post('/api/talk/request',headers=a,json={'target_id':ub['id']}).json()['id']
 assert c.post('/api/talk/request',headers=a,json={'target_id':ub['id']}).json()['id']==id
 assert c.post('/api/talk/'+id+'/reject',headers=b,json={}).status_code==200
 assert c.post('/api/talk/request',headers=a,json={'target_id':ub['id']}).status_code==429
 with db.begin() as d:d.get(MediaSession,id).ended_at=time.time()-60;d.get(MediaSession,id).created_at=time.time()-180
 id=c.post('/api/talk/request',headers=a,json={'target_id':ub['id']}).json()['id']
 with db.begin() as d:d.get(MediaSession,id).created_at=time.time()-130
 assert c.post('/api/talk/'+id+'/accept',headers=b,json={}).status_code==409
 assert c.get('/api/talk/state',headers=b).json()[0]['state']=='expired'

def test_privacy_distance_block_membership(system):
 c,db,a,ua,b,ub=pair(system);third,ut=register(c,'talkthird');onboard(c,third)
 assert c.put('/api/talk/preferences',headers=b,json={'text':'nobody','voice':'nobody','liveface':'nobody'}).status_code==200
 assert c.post('/api/talk/request',headers=a,json={'target_id':ub['id']}).status_code==403
 c.put('/api/talk/preferences',headers=b,json={'text':'nearby'})
 with db.begin() as d:d.get(Presence,ub['id']).x=300
 assert c.post('/api/talk/request',headers=a,json={'target_id':ub['id']}).status_code==403
 with db.begin() as d:d.get(Presence,ub['id']).x=d.get(Presence,ua['id']).x
 id=c.post('/api/talk/request',headers=a,json={'target_id':ub['id']}).json()['id'];c.post('/api/talk/'+id+'/accept',headers=b,json={})
 assert c.post('/api/talk/'+id+'/messages',headers=third,json={'id':str(uuid.uuid4()),'body':'intrusion'}).status_code==403
 c.post('/api/social/'+ua['id']+'/block',headers=b,json={})
 assert c.post('/api/talk/'+id+'/messages',headers=a,json={'id':str(uuid.uuid4()),'body':'blocked'}).status_code==403

def test_message_replay_media_consent(system):
 c,db,a,ua,b,ub=pair(system)
 for kind in ['text','voice','liveface']:
  id=c.post('/api/talk/request',headers=a,json={'target_id':ub['id'],'kind':kind}).json()['id']
  if kind!='text':assert c.post('/api/media/'+id+'/token',headers=a,json={}).status_code==403
  assert c.post('/api/talk/'+id+'/accept',headers=b,json={}).status_code==200
  if kind=='text':
   body={'id':str(uuid.uuid4()),'body':'Once'}
   assert c.post('/api/talk/'+id+'/messages',headers=a,json=body).status_code==201
   assert c.post('/api/talk/'+id+'/messages',headers=a,json=body).status_code==201
   assert len(c.get('/api/talk/state',headers=b).json()[0]['messages'])==1
  else:assert c.post('/api/media/'+id+'/token',headers=a,json={}).status_code==503

def test_oauth_not_configured_and_state_guard(system,monkeypatch):
 c,_=system
 for provider in ['GOOGLE','APPLE','FACEBOOK']:
  monkeypatch.delenv(provider+'_CLIENT_ID',raising=False);monkeypatch.delenv(provider+'_CLIENT_SECRET',raising=False)
 assert not any(c.get('/api/oauth/providers').json().values())
 assert c.get('/api/oauth/google/start?adult=true&terms=true').status_code==503
 assert c.get('/api/oauth/google/callback?state=invalid&code=invalid').status_code==403
