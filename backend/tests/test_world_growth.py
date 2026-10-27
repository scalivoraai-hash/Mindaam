import time,uuid,os,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from sqlalchemy import select,func,create_engine,text
from backend.tests.test_core import system,register,onboard
from backend.api.growth import WorldAccess,ShareAction,GrowthEvent,ShareInvite
from backend.api.models import Session,Presence

def choice(c,h,city,confirmed=True):return c.post(f'/api/growth/worlds/{city}/starter',headers=h,json={'confirmed':confirmed})
def state(c,h):return c.get('/api/growth/worlds',headers=h).json()
def four(c,h):
 for city in ['manchester','milton-keynes','edinburgh']:assert choice(c,h,city).status_code==200

def test_first_four_are_user_chosen_atomic_and_permanent(system):
 c,dbs=system;h,u=register(c,'freeworlds');assert state(c,h)['starter_selected']==0
 onboard(c,h);assert state(c,h)['starter_selected']==1
 assert c.post('/api/world/enter',headers=h,json={'city':'manchester'}).status_code==403
 assert choice(c,h,'manchester',False).status_code==409
 assert choice(c,h,'manchester').json()['starter_selected']==2
 assert choice(c,h,'manchester').json()['starter_selected']==2
 assert choice(c,h,'milton-keynes').json()['starter_selected']==3
 assert choice(c,h,'edinburgh',False).status_code==409
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda city:choice(c,h,city),['edinburgh','bristol']))
 assert sorted(r.status_code for r in results)==[200,403]
 s=state(c,h);assert s['starter_selected']==4
 assert len([w for w in s['worlds'] if w['access']=='owned'])==4
 locked=next(w for w in s['worlds'] if w['access']=='locked')
 assert c.post('/api/world/enter',headers=h,json={'city':locked['id']}).json()['detail']['code']=='WORLD_LOCKED'
 assert c.post('/api/places/travel/visit',headers=h,json={'city':locked['id'],'place_id':'1'}).status_code==403
 assert c.post('/api/onboarding',headers=h,json={'city':locked['id']}).status_code==403
 assert state(c,h)['starter_selected']==4

def test_share_progress_idempotency_channels_cooldown_and_login_persistence(system,monkeypatch):
 c,dbs=system;h,u=register(c,'shareworlds');onboard(c,h);four(c,h)
 inv=c.post('/api/growth/worlds/bristol/invite',headers=h).json()
 assert u['id'] not in inv['path']
 assert inv==c.post('/api/growth/worlds/bristol/invite',headers=h).json()
 assert 'user_id' not in c.get('/api/growth/invites/'+inv['code']).json()
 def share(channel='whatsapp',id=None):return c.post('/api/growth/worlds/bristol/share',headers=h,json={'share_action_id':id or str(uuid.uuid4()),'channel':channel,'outcome':'copied' if channel=='copy' else 'handoff' if channel in {'email','sms'} else 'opened','invite_code':inv['code']})
 first=str(uuid.uuid4());assert share(id=first).json()['counted']
 # Exercise the cooldown independently of slow CI/database response time.
 from types import SimpleNamespace
 from backend.api import growth
 with dbs() as db:now=db.scalar(select(ShareAction.created_at).where(ShareAction.user_id==u['id']))
 monkeypatch.setattr(growth,'time',SimpleNamespace(time=lambda:now))
 assert share(id=first).json()['duplicate']
 assert share().status_code==429
 for channel in ['facebook','x','copy']:
  with dbs.begin() as db:
   for a in db.scalars(select(ShareAction).where(ShareAction.user_id==u['id'])):a.created_at=now-10
  r=share(channel);assert r.status_code==200,r.text
 s=state(c,h);w=next(w for w in s['worlds'] if w['id']=='bristol');assert w['access']=='owned' and w['shares']==4
 assert next(w for w in s['worlds'] if w['id']=='oxford')['shares']==0
 assert share().status_code==429
 assert c.post('/api/world/enter',headers=h,json={'city':'bristol'}).status_code==200
 assert c.post('/api/auth/logout',headers=h).status_code==200
 login=c.post('/api/auth/login',json={'identifier':'shareworlds','password':'A secure test password 2026!'})
 assert login.status_code==200
 h2={'Authorization':'Bearer '+login.json()['token']}
 assert next(w for w in state(c,h2)['worlds'] if w['id']=='bristol')['access']=='owned'
 with dbs() as db:assert db.scalar(select(func.count()).select_from(WorldAccess).where(WorldAccess.user_id==u['id'],WorldAccess.destination_id=='bristol'))==1

def test_share_cross_user_and_outcome_validation(system):
 c,dbs=system;h,u=register(c,'shareguard');onboard(c,h);four(c,h);other,_=register(c,'shareother');onboard(c,other)
 inv=c.post('/api/growth/worlds/york/invite',headers=h).json()
 body={'share_action_id':str(uuid.uuid4()),'channel':'native','outcome':'opened','invite_code':inv['code']}
 assert c.post('/api/growth/worlds/york/share',headers=h,json=body).status_code==422
 body['outcome']='shared'
 assert c.post('/api/growth/worlds/york/share',headers=other,json=body).status_code==403
 assert c.post('/api/growth/worlds/oxford/share',headers=h,json=body).status_code==403
 assert c.post('/api/growth/worlds/york/share',headers=h,json=body).status_code==200
 assert c.get('/api/growth/metrics',headers=h).status_code==403

def test_flat_catalog_real_counts_and_public_invite(system):
 c,dbs=system;h,u=register(c,'growthcounts');onboard(c,h)
 c.post('/api/world/enter',headers=h,json={'city':'london'})
 rows=state(c,h)['worlds'];assert len(rows)==45
 assert len([w for w in rows if w['name'].startswith('Milton Keynes -')])==3
 assert next(w for w in rows if w['id']=='london')['online']==1
 assert choice(c,h,'manchester').status_code==200
 c.post('/api/world/enter',headers=h,json={'city':'manchester'})
 rows=state(c,h)['worlds'];assert next(w for w in rows if w['id']=='london')['online']==0
 assert next(w for w in rows if w['id']=='manchester')['online']==1
 with dbs.begin() as db:db.get(Presence,u['id']).updated_at=time.time()-46
 assert next(w for w in state(c,h)['worlds'] if w['id']=='manchester')['online']==0

def test_migration_preserves_all_preexisting_world_access(tmp_path):
 url='sqlite:///'+str(tmp_path/'legacy.db');root=Path(__file__).resolve().parents[2]
 env={**os.environ,'DATABASE_URL':url,'APP_ENV':'test'}
 def migrate(to):
  r=subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade',to],cwd=root,env=env,capture_output=True,text=True);assert r.returncode==0,r.stderr
 migrate('fg21_social_events');engine=create_engine(url)
 with engine.begin() as db:db.execute(text("INSERT INTO users (id,email,username,password_hash,role,city,privacy,avatar,profile,interests,onboarded,suspended,verified,location_consent,analytics_consent,created_at) VALUES ('legacy','legacy@example.test','legacy','unused','consumer','london','City Mode','{}','{}','[]',true,false,false,false,false,1)"))
 migrate('head')
 with engine.connect() as db:
  assert db.scalar(text("SELECT count(*) FROM world_access WHERE user_id='legacy' AND source='legacy'"))==17
 engine.dispose()

def test_fourth_share_race_cannot_duplicate_access(system):
 c,dbs=system;h,u=register(c,'sharerace');onboard(c,h);four(c,h)
 inv=c.post('/api/growth/worlds/york/invite',headers=h).json()
 with dbs.begin() as db:
  for _ in range(3):db.add(ShareAction(id=str(uuid.uuid4()),user_id=u['id'],destination_id='york',channel='copy',outcome='copied',created_at=time.time()-10))
 body={'share_action_id':str(uuid.uuid4()),'channel':'copy','outcome':'copied','invite_code':inv['code']}
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:c.post('/api/growth/worlds/york/share',headers=h,json=body),range(2)))
 assert all(r.status_code==200 for r in results)
 with dbs() as db:
  assert db.scalar(select(func.count()).select_from(ShareAction).where(ShareAction.user_id==u['id']))==4
  assert db.scalar(select(func.count()).select_from(WorldAccess).where(WorldAccess.user_id==u['id'],WorldAccess.destination_id=='york'))==1

def test_another_destinations_progress_is_saved_independently(system):
 c,dbs=system;h,u=register(c,'twoinvites');onboard(c,h);four(c,h)
 for city,n in [('bristol',2),('oxford',1)]:
  inv=c.post(f'/api/growth/worlds/{city}/invite',headers=h).json()
  for _ in range(n):
   with dbs.begin() as db:
    for a in db.scalars(select(ShareAction).where(ShareAction.user_id==u['id'])):a.created_at=time.time()-10
   r=c.post(f'/api/growth/worlds/{city}/share',headers=h,json={'share_action_id':str(uuid.uuid4()),'channel':'copy','outcome':'copied','invite_code':inv['code']});assert r.status_code==200
 rows={w['id']:w for w in state(c,h)['worlds']}
 assert rows['bristol']['shares']==2 and rows['oxford']['shares']==1
 assert rows['bristol']['access']==rows['oxford']['access']=='locked'
