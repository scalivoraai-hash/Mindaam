import time
from backend.tests.test_core import system, register
from backend.tests.test_talk import pair
from backend.tests.test_commerce import commerce, setup_business
from backend.api.models import MediaSession, Presence
from backend.api.commerce import Business, world_businesses
from backend.api.geography import district

def test_cookie_username_password_and_csrf(system, monkeypatch):
 c,db=system
 monkeypatch.setenv('PUBLIC_ORIGIN','http://testserver')
 h={'Origin':'http://testserver','X-Pulse-Client':'web'}
 body={'email':'closure@example.test','username':'Closure','password':'LongTestPassword1!','confirm_password':'different','adult':True,'accepted_terms':True,'accepted_privacy':True}
 assert c.post('/api/auth/register',headers=h,json=body).status_code==422
 body['confirm_password']=body['password'];body['accepted_privacy']=False
 assert c.post('/api/auth/register',headers=h,json=body).status_code==422
 body['accepted_privacy']=True
 r=c.post('/api/auth/register',headers=h,json=body)
 assert r.status_code==201,r.text
 assert 'token' not in r.json() and 'HttpOnly' in r.headers['set-cookie']
 assert c.get('/api/me').status_code==200
 assert c.post('/api/auth/logout',json={}).status_code==403
 with c.websocket_connect('/api/realtime',headers={'origin':'http://testserver'}) as ws:
  ws.send_json({});assert ws.receive_json()['type']=='state'
 assert c.post('/api/auth/logout',headers=h,json={}).status_code==200
 assert c.get('/api/me').status_code==401
 assert c.post('/api/auth/login',headers=h,json={'identifier':' cLoSuRe ','password':body['password']}).status_code==200
 assert c.post('/api/auth/change-password',headers=h,json={'current_password':body['password'],'password':'ChangedPassword2!','confirm_password':'ChangedPassword2!'}).status_code==200
 assert c.get('/api/me').status_code==401
 assert c.post('/api/auth/login',headers=h,json={'identifier':body['email'],'password':body['password']}).status_code==401
 assert c.post('/api/auth/login',headers=h,json={'identifier':'closure','password':'ChangedPassword2!'}).status_code==200

def test_short_invitation_cancel_and_proximity(system):
 c,db,a,ua,b,ub=pair(system)
 with db.begin() as d:
  pa=d.get(Presence,ua['id']);pb=d.get(Presence,ub['id']);pb.x=pa.x+11;pb.z=pa.z
 assert c.post('/api/talk/request',headers=a,json={'target_id':ub['id']}).status_code==403
 with db.begin() as d:d.get(Presence,ub['id']).x=d.get(Presence,ua['id']).x+4
 id=c.post('/api/talk/request',headers=a,json={'target_id':ub['id']}).json()['id']
 assert c.post('/api/talk/'+id+'/cancel',headers=b,json={}).status_code==403
 assert c.post('/api/talk/'+id+'/cancel',headers=a,json={}).status_code==200
 assert c.post('/api/talk/'+id+'/accept',headers=b,json={}).status_code==409
 with db.begin() as d:
  row=d.get(MediaSession,id);row.state='pending';row.created_at=time.time()-31;row.ended_at=None
 assert c.post('/api/talk/'+id+'/accept',headers=b,json={}).status_code==409

def test_storefront_owner_and_verified_map(commerce):
 c,db=commerce;b=setup_business(commerce)
 r=c.put('/api/businesses/'+b+'/signage',headers={'x-user':'other'},json={'category':'Cafe'})
 assert r.status_code==404
 r=c.put('/api/businesses/'+b+'/signage',headers={'x-user':'owner'},json={'category':'Cafe','colour':'#123456','logo_url':'javascript:bad'})
 assert r.status_code==422
 r=c.put('/api/businesses/'+b+'/signage',headers={'x-user':'owner'},json={'category':'Cafe','colour':'#123456'})
 assert r.status_code==200,r.text
 origin=district('london')['origin']
 with db.begin() as d:
  business=d.get(Business,b);business.latitude=origin['lat'];business.longitude=origin['lon'];business.status='verified'
  result=world_businesses(d,'london',0,0)
  assert len(result)==1 and result[0]['signage']['category']=='Cafe'
  assert result[0]['visit_reward']==0
  business.status='pending';d.flush();assert world_businesses(d,'london',0,0)==[]

def test_mail_worker_delivers_off_event_loop(monkeypatch):
 import asyncio,threading
 from backend.api import main,identity
 loop_thread=threading.get_ident();workers=[]
 monkeypatch.setenv('SMTP_HOST','test.invalid');monkeypatch.setenv('MAIL_ENCRYPTION_KEY','test-only')
 monkeypatch.setattr(identity,'drain_outbox',lambda limit:workers.append(threading.get_ident()))
 async def stop(_):raise asyncio.CancelledError()
 monkeypatch.setattr(main.asyncio,'sleep',stop)
 async def run():
  try:await main.deliver_mail()
  except asyncio.CancelledError:pass
 asyncio.run(run())
 assert workers and workers[0]!=loop_thread
