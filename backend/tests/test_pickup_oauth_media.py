import asyncio,threading,time
from urllib.parse import urlparse,parse_qs
from types import SimpleNamespace
import pytest,jwt
from backend.tests.test_core import system,register,onboard
from backend.api import oauth
from backend.api.models import User
from sqlalchemy import select,func

def test_pickup_exact_awards_and_replay(system):
 c,_=system;h,u=register(c,'autograb');onboard(c,h)
 first=c.post('/api/collectibles/london-local-0/claim',headers=h).json()
 assert first['awarded_xp']==5 and first['awarded_credits']==0
 replay=c.post('/api/collectibles/london-local-0/claim',headers=h).json()
 assert replay['awarded_xp']==0 and replay['awarded_credits']==0
 assert c.get('/api/inventory',headers=h).json()['total']==1

def test_text_consent_cannot_mint_camera_token_and_kind_dedup(system):
 c,_=system;a,ua=register(c,'caller');b,ub=register(c,'receiver')
 onboard(c,a);onboard(c,b)
 text=c.post('/api/talk/request',headers=a,json={'target_id':ub['id'],'kind':'text'}).json()
 assert c.post('/api/talk/'+text['id']+'/accept',headers=b).status_code==200
 assert c.post('/api/media/'+text['id']+'/token',headers=a).status_code==403
 voice=c.post('/api/media/request',headers=a,json={'target_id':ub['id'],'kind':'voice'}).json()
 reverse=c.post('/api/media/request',headers=b,json={'target_id':ua['id'],'kind':'voice'}).json()
 assert voice['id']==reverse['id'] and voice['id']!=text['id']
 assert c.post('/api/media/'+voice['id']+'/accept',headers=b).status_code==200
 assert c.post('/api/media/'+voice['id']+'/end',headers=a).status_code==200
 assert c.post('/api/media/'+voice['id']+'/token',headers=a).status_code==403

def test_oauth_database_callback_runs_off_event_loop(monkeypatch):
 seen=[];loop_thread=threading.get_ident()
 monkeypatch.setattr(oauth,'callback_sync',lambda *args:seen.append(threading.get_ident()))
 request=SimpleNamespace(method='GET',query_params={},cookies={})
 asyncio.run(oauth.callback('google',request,None))
 assert seen and seen[0]!=loop_thread

@pytest.fixture
def google(system,monkeypatch):
 from cryptography.hazmat.primitives.asymmetric import rsa
 key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
 monkeypatch.setenv('GOOGLE_CLIENT_ID','unit-test-client')
 monkeypatch.setenv('GOOGLE_CLIENT_SECRET','unit-test-secret')
 monkeypatch.setenv('PUBLIC_ORIGIN','http://testserver')
 monkeypatch.setattr(oauth.jwt,'PyJWKClient',lambda url:SimpleNamespace(get_signing_key_from_jwt=lambda token:SimpleNamespace(key=key.public_key())))
 state={}
 class Provider:
  def __init__(self,**kwargs):pass
  def __enter__(self):return self
  def __exit__(self,*args):pass
  def post(self,url,data):
   assert data['code_verifier']
   return SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'id_token':state['token']})
 monkeypatch.setattr(oauth.httpx,'Client',Provider)
 c,sessions=system
 def login(email='google-user@example.test',subject='google-subject',verified=True,claims_override=None):
  start=c.get('/api/oauth/google/start?adult=true&terms=true',follow_redirects=False)
  assert start.status_code==303
  args=parse_qs(urlparse(start.headers['location']).query)
  claims={'iss':'https://accounts.google.com','aud':'unit-test-client','sub':subject,'iat':int(time.time()),'exp':int(time.time())+60,'nonce':args['nonce'][0],'email':email,'email_verified':verified}
  claims.update(claims_override or {})
  state['token']=jwt.encode(claims,key,algorithm='RS256')
  callback=c.get('/api/oauth/google/callback',params={'state':args['state'][0],'code':'unit-code'},follow_redirects=False)
  return callback
 return c,sessions,login

def test_google_new_returning_logout_and_same_identity(google):
 c,sessions,login=google
 assert login().headers['location']=='/?oauth=complete'
 first=c.post('/api/oauth/complete',headers={'origin':'http://testserver'}).json()
 h={'Authorization':'Bearer '+first['token']}
 assert c.get('/api/me',headers=h).json()['id']==first['user']['id']
 assert c.post('/api/auth/logout',headers=h).status_code==200
 assert c.get('/api/me',headers=h).status_code==401
 assert login().headers['location']=='/?oauth=complete'
 second=c.post('/api/oauth/complete',headers={'origin':'http://testserver'}).json()
 assert first['user']['id']==second['user']['id']
 with sessions() as db:assert db.scalar(select(func.count()).select_from(User).where(User.email=='google-user@example.test'))==1

def test_google_existing_email_requires_explicit_link_and_unverified_fails(google):
 c,_,login=google
 register(c,'existing')
 assert login(email='existing@example.test').headers['location']=='/?oauth_error=link_existing'
 assert login(email='unverified@example.test',subject='unverified',verified=False).headers['location']=='/?oauth_error=provider_failed'

@pytest.mark.parametrize('override',[{'aud':'wrong'},{'iss':'https://wrong.invalid'},{'nonce':'wrong'},{'exp':1}])
def test_google_rejects_invalid_signed_claims(google,override):
 c,_,login=google
 assert login(claims_override=override).headers['location']=='/?oauth_error=provider_failed'
