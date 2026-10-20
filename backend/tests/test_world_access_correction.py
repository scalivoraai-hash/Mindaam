import json,time,uuid,os,subprocess,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,func,create_engine,text
from backend.tests.test_core import system,register,onboard
from backend.api.expansion import Destination,INTERNATIONAL
from backend.api.growth import WorldAccess,ShareAction
from backend.api.models import User,Presence,Session as AuthSession,Event
from backend.api.discovery import CityInterest

def test_mixed_starters_four_shares_and_real_international_presence(system):
 c,dbs=system;h,u=register(c,'mixedworlds');onboard(c,h)
 assert c.get('/api/growth/worlds',headers=h).json()['starter_selected']==1
 for n,city in [(2,'dubai'),(3,'tokyo')]:
  r=c.post(f'/api/growth/worlds/{city}/starter',headers=h,json={'confirmed':True});assert r.status_code==200,r.text
  assert r.json()['starter_selected']==n
 assert c.post('/api/growth/worlds/new-york/starter',headers=h,json={}).status_code==409
 assert c.get('/api/growth/worlds',headers=h).json()['starter_selected']==3
 assert c.post('/api/growth/worlds/new-york/starter',headers=h,json={'confirmed':True}).json()['starter_selected']==4
 for path in ['/api/world/paris','/api/world/enter']:
  r=c.get(path,headers=h) if path.endswith('paris') else c.post(path,headers=h,json={'city':'paris'})
  assert r.status_code==403 and r.json()['detail']['share_goal']==4
 assert c.post('/api/destinations/paris/interest',headers=h,json={}).status_code==422
 assert c.post('/api/destinations/paris/share-link',headers=h).status_code==404
 inv=c.post('/api/growth/worlds/paris/invite',headers=h).json()
 for n,(channel,outcome) in enumerate([('whatsapp','opened'),('facebook','opened'),('native','shared'),('copy','copied')],1):
  with dbs.begin() as db:
   for a in db.scalars(select(ShareAction).where(ShareAction.user_id==u['id'])):a.created_at=time.time()-10
  body={'share_action_id':str(uuid.uuid4()),'channel':channel,'outcome':outcome,'invite_code':inv['code']}
  r=c.post('/api/growth/worlds/paris/share',headers=h,json=body);assert r.status_code==200,r.text
  w=next(w for w in r.json()['worlds'] if w['id']=='paris')
  assert w['shares']==n and w['access']==('owned' if n==4 else 'locked')
  assert c.post('/api/growth/worlds/paris/share',headers=h,json=body).json()['duplicate']
 assert c.post('/api/world/enter',headers=h,json={'city':'paris'}).status_code==200
 assert next(d for d in c.get('/api/cities').json() if d['id']=='paris')['online']==1
 assert c.post('/api/world/enter',headers=h,json={'city':'dubai'}).status_code==200
 rows={d['id']:d for d in c.get('/api/cities').json()};assert rows['paris']['online']==0 and rows['dubai']['online']==1
 with dbs.begin() as db:db.get(Presence,u['id']).updated_at=time.time()-46
 assert next(d for d in c.get('/api/cities').json() if d['id']=='dubai')['online']==0
 assert c.post('/api/auth/logout',headers=h).status_code==200
 login=c.post('/api/auth/login',json={'identifier':'mixedworlds','password':'A secure test password 2026!'})
 h2={'Authorization':'Bearer '+login.json()['token']}
 assert c.post('/api/world/enter',headers=h2,json={'city':'paris'}).status_code==200

def test_request_country_catalogue_custom_review_dedup_and_spam(system):
 c,dbs=system;a,ua=register(c,'places_a');b,ub=register(c,'places_b')
 rows=c.get('/api/request-places').json()['countries'];by={r['country']:r for r in rows}
 assert {'Chicago','Las Vegas','Boston','Washington DC','Seattle','Austin','Houston','Orlando','San Diego'}<={d['name'] for d in by['US']['places']}
 assert {'Beijing','Shenzhen','Guangzhou','Chengdu','Hangzhou','Xi’an'}<={d['name'] for d in by['CN']['places']}
 assert not any(d['status']=='ACTIVE' for row in rows for d in row['places'])
 assert c.post('/api/request-places',headers=a,json={'country':'FR','name':'PARIS'}).json()['detail']['code']=='USE_WORLD_ACCESS'
 for name in ['https://spam.test','123456','🔥🔥','A']:
  assert c.post('/api/request-places',headers=a,json={'country':'US','name':name}).status_code==422
 body={'country':'US','name':'Testborough'} # Isolated SQLite fixture, never a production city.
 with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(lambda _:c.post('/api/request-places',headers=a,json=body),range(3)))
 assert all(r.status_code==201 for r in results)
 id=results[0].json()['id'];assert len({r.json()['id'] for r in results})==1
 assert sum(r.json()['counted'] for r in results)==1
 assert c.post('/api/request-places',headers=b,json={**body,'name':'  TESTBOROUGH '}).json()['id']==id
 assert id not in {d['id'] for d in c.get('/api/cities').json()}
 assert c.post(f'/api/destinations/{id}/share-link',headers=a).status_code==404
 with dbs.begin() as db:
  assert db.scalar(select(func.count()).select_from(CityInterest).where(CityInterest.city==id))==2
  db.get(User,ua['id']).role='super_admin'
 admin=c.get('/api/super-admin/demand',headers=a).json();assert any(d['id']==id for d in admin['destinations'])
 assert c.put('/api/super-admin/destinations/'+id,headers=a,json={'name':'Testborough','country':'US','status':'REQUESTABLE','public':True,'joinable':False,'threshold':2}).json()['status']=='QUALIFIED'
 for name in ['Exampleton','Sampleville']:
  assert c.post('/api/request-places',headers=b,json={**body,'name':name}).status_code==201
 assert c.post('/api/request-places',headers=b,json={**body,'name':'Fourthville'}).status_code==429

def test_launch_maps_are_real_attributed_and_have_safe_spawn():
 from backend.api.geography import district,traversable,road_segments
 for id,*_ in INTERNATIONAL:
  d=district(id)
  assert d['source']=='OpenStreetMap contributors' and d['license']=='ODbL 1.0'
  assert len(d['source_sha256'])==64 and len(road_segments(id))>=5
  assert any(f['tags'].get('building') for f in d['features'])
  assert traversable(id,*d['spawn']),id

def test_correction_migration_preserves_ids_interest_and_unlocks_four_old_shares(tmp_path):
 root=Path(__file__).resolve().parents[2];url='sqlite:///'+str(tmp_path/'correction.db')
 def migrate(to):
  r=subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade',to],cwd=root,env={**os.environ,'DATABASE_URL':url,'APP_ENV':'test'},capture_output=True,text=True)
  assert r.returncode==0,r.stderr
 migrate('fk25_social_mobility');engine=create_engine(url)
 with engine.begin() as db:
  db.execute(text("INSERT INTO users (id,email,username,password_hash,role,city,privacy,avatar,profile,interests,onboarded,suspended,verified,location_consent,analytics_consent,created_at) VALUES ('preserved','preserved@example.test','preserved','unused','consumer','london','City Mode','{}','{}','[]',true,false,false,false,false,1)"))
  db.execute(text("UPDATE destinations SET status='REQUESTABLE' WHERE id='paris'"))
  db.execute(text("INSERT INTO city_interests (user_id,city,created_at,source,invite_code) VALUES ('preserved','paris',1,'legacy','')"))
  db.execute(text("INSERT INTO world_access VALUES ('preserved','london','starter',1)"))
  for n in range(4):db.execute(text("INSERT INTO world_share_actions VALUES (:id,'preserved','paris','copy','copied',:t)"),{'id':str(uuid.uuid4()),'t':n+1})
 migrate('head');migrate('head')
 with engine.connect() as db:
  assert db.scalar(text("SELECT status FROM destinations WHERE id='paris'"))=='ACTIVE'
  assert db.scalar(text("SELECT count(*) FROM city_interests WHERE user_id='preserved' AND city='paris'"))==1
  assert db.scalar(text("SELECT count(*) FROM world_access WHERE user_id='preserved'"))==2
  assert db.scalar(text("SELECT source FROM world_access WHERE user_id='preserved' AND destination_id='paris'"))=='share'
  assert db.scalar(text("SELECT count(*) FROM world_share_actions WHERE user_id='preserved'"))==4
 engine.dispose()
