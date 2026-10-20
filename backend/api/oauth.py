"""OAuth authorization-code login with state/nonce validation and explicit linking."""
import os,time,secrets,hashlib,base64
from urllib.parse import urlencode,parse_qs
import httpx,jwt
from fastapi import APIRouter,Depends,HTTPException,Request
from starlette.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse,JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Column,String,Float,ForeignKey,select
from .db import Base,get_db
from .models import User,Consent
from .auth import current_user,hash_password,session_token,public_user,login_result
router=APIRouter(prefix='/api/oauth')
PROVIDERS={
 'google':{'auth':'https://accounts.google.com/o/oauth2/v2/auth','token':'https://oauth2.googleapis.com/token','jwks':'https://www.googleapis.com/oauth2/v3/certs','issuer':['https://accounts.google.com','accounts.google.com'],'scope':'openid email profile'},
 'apple':{'auth':'https://appleid.apple.com/auth/authorize','token':'https://appleid.apple.com/auth/token','jwks':'https://appleid.apple.com/auth/keys','issuer':'https://appleid.apple.com','scope':'name email'},
 'facebook':{'auth':'https://www.facebook.com/dialog/oauth','token':'https://graph.facebook.com/oauth/access_token','scope':'email,public_profile'}}
class OAuthFlow(Base):
 __tablename__='oauth_flows'
 id=Column(String(64),primary_key=True)
 provider=Column(String(20),nullable=False)
 nonce=Column(String(100),nullable=False)
 verifier=Column(String(100),nullable=False)
 user_id=Column(ForeignKey('users.id'),nullable=True)
 expires_at=Column(Float,nullable=False)
class OAuthIdentity(Base):
 __tablename__='oauth_identities'
 provider=Column(String(20),primary_key=True)
 subject=Column(String(255),primary_key=True)
 user_id=Column(ForeignKey('users.id'),nullable=False)
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def config(provider):
 if provider not in PROVIDERS:raise HTTPException(404,'Unknown sign-in provider')
 client=os.getenv(provider.upper()+'_CLIENT_ID');secret=os.getenv(provider.upper()+'_CLIENT_SECRET')
 if not client or not secret:raise HTTPException(503,provider.title()+' sign-in is not configured')
 return {**PROVIDERS[provider],'client':client,'secret':secret}
def origin():return os.getenv('PUBLIC_ORIGIN','http://localhost:3000').rstrip('/')
@router.get('/providers')
def providers():return {p:bool(os.getenv(p.upper()+'_CLIENT_ID') and os.getenv(p.upper()+'_CLIENT_SECRET')) for p in PROVIDERS}
def start(provider,db,user=None):
 c=config(provider);state=secrets.token_urlsafe(32);nonce=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
 db.add(OAuthFlow(id=digest(state),provider=provider,nonce=nonce,verifier=verifier,user_id=user.id if user else None,expires_at=time.time()+600))
 args={'client_id':c['client'],'redirect_uri':origin()+'/api/oauth/'+provider+'/callback','response_type':'code','scope':c['scope'],'state':state,'nonce':nonce}
 if provider=='google':args.update(code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('='),code_challenge_method='S256')
 if provider=='apple':args['response_mode']='form_post'
 response=RedirectResponse(c['auth']+'?'+urlencode(args),status_code=303);response.set_cookie('pulse-oauth-state',state,max_age=600,httponly=True,secure=origin().startswith('https'),samesite='none' if provider=='apple' else 'lax',path='/api/oauth');return response
@router.get('/{provider}/start')
def begin(provider:str,adult:bool=False,terms:bool=False,db=Depends(get_db)):
 if not adult or not terms:raise HTTPException(422,'Confirm age 18+ and accept the terms before continuing')
 return start(provider,db)
@router.post('/{provider}/link')
def link(provider:str,u=Depends(current_user),db=Depends(get_db)):
 response=start(provider,db,u)
 # Fetch receives a URL, preserving HttpOnly state binding without following redirects.
 result=JSONResponse({'url':response.headers['location']});result.headers['set-cookie']=response.headers['set-cookie'];return result
@router.api_route('/{provider}/callback',methods=['GET','POST'])
async def callback(provider:str,request:Request,db=Depends(get_db)):
 params=dict(request.query_params) if request.method=='GET' else {k:v[0] for k,v in parse_qs((await request.body()).decode()).items()}
 return await run_in_threadpool(callback_sync,provider,params,request.cookies.get('pulse-oauth-state',''),db)
def callback_sync(provider,params,cookie,db):
 state=params.get('state','')
 if not state or not cookie or not secrets.compare_digest(state,cookie):raise HTTPException(403,'Sign-in state mismatch; start again')
 flow=db.scalar(select(OAuthFlow).where(OAuthFlow.id==digest(state)).with_for_update())
 if not flow or flow.provider!=provider or flow.expires_at<time.time():raise HTTPException(403,'Sign-in expired')
 flow.expires_at=0
 # Consume state and release the transaction before any external provider I/O.
 db.commit()
 if params.get('error') or not params.get('code'):return RedirectResponse('/?oauth_error=cancelled',status_code=303)
 c=config(provider)
 try:
  with httpx.Client(timeout=15) as client:
   data={'client_id':c['client'],'client_secret':c['secret'],'code':params['code'],'grant_type':'authorization_code','redirect_uri':origin()+'/api/oauth/'+provider+'/callback'}
   if provider=='google':data['code_verifier']=flow.verifier
   response=client.post(c['token'],data=data);response.raise_for_status();token=response.json()
   if provider=='facebook':
    profile=client.get('https://graph.facebook.com/me',params={'fields':'id,name,email'},headers={'Authorization':'Bearer '+token['access_token']});profile.raise_for_status();claims=profile.json();subject=claims['id'];email=claims.get('email');verified=False
   else:
    encoded=token['id_token'];key=jwt.PyJWKClient(c['jwks']).get_signing_key_from_jwt(encoded)
    claims=jwt.decode(encoded,key.key,algorithms=['RS256'],audience=c['client'],issuer=c['issuer'],options={'require':['exp','iat','sub','iss','aud','nonce']})
    if not secrets.compare_digest(claims['nonce'],flow.nonce):raise ValueError('nonce mismatch')
    subject=claims['sub'];email=claims.get('email');verified=claims.get('email_verified') in [True,'true']
  if provider=='google' and (not email or not verified):raise ValueError('Google must supply a verified email address')
  identity=db.get(OAuthIdentity,(provider,subject));user=db.get(User,identity.user_id) if identity else None
  if flow.user_id:
   if user and user.id!=flow.user_id:raise ValueError('Provider identity is already linked')
   user=db.get(User,flow.user_id)
  if not user:
   if not email:raise ValueError('The provider did not supply an email address')
   if db.scalar(select(User).where(User.email==email.lower())):return RedirectResponse('/?oauth_error=link_existing',status_code=303)
   user=User(email=email.lower(),username='Explorer '+secrets.token_hex(4),password_hash=hash_password(secrets.token_urlsafe(50)),city='milton-keynes',verified=verified)
   db.add(user);db.flush()
   db.add(Consent(user_id=user.id,document='terms',accepted=True));db.add(Consent(user_id=user.id,document='adult',accepted=True))
  if user.suspended:raise ValueError('Account unavailable')
  if not identity:db.add(OAuthIdentity(provider=provider,subject=subject,user_id=user.id));db.flush()
  grant=secrets.token_urlsafe(40);db.add(OAuthFlow(id=digest(grant),provider='complete',nonce='',verifier='',user_id=user.id,expires_at=time.time()+60))
  response=RedirectResponse('/?oauth=complete',status_code=303);response.delete_cookie('pulse-oauth-state',path='/api/oauth');response.set_cookie('pulse-oauth-grant',grant,max_age=60,httponly=True,secure=origin().startswith('https'),samesite='lax',path='/api/oauth');return response
 except IntegrityError:
  db.rollback();return RedirectResponse('/?oauth_error=link_existing',status_code=303)
 except (httpx.HTTPError,jwt.PyJWTError,ValueError,KeyError):return RedirectResponse('/?oauth_error=provider_failed',status_code=303)
@router.post('/complete')
def complete(request:Request,db=Depends(get_db)):
 if request.headers.get('origin')!=origin():raise HTTPException(403,'Invalid origin')
 grant=request.cookies.get('pulse-oauth-grant','');flow=db.scalar(select(OAuthFlow).where(OAuthFlow.id==digest(grant),OAuthFlow.provider=='complete').with_for_update())
 if not flow or flow.expires_at<time.time():raise HTTPException(403,'Sign-in handoff expired')
 u=db.get(User,flow.user_id)
 if not u or u.suspended:raise HTTPException(403,'Account unavailable')
 flow.expires_at=0;response=JSONResponse({});payload=login_result(db,u,request,response);response.body=__import__('json').dumps(payload).encode();response.headers['content-length']=str(len(response.body));response.delete_cookie('pulse-oauth-grant',path='/api/oauth');return response
