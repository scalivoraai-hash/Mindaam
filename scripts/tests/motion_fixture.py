"""Movement measurements on real mapped roads in a disposable local database."""
import os,sys,json,time,math
if os.getenv('APP_ENV')!='local' or not os.getenv('DATABASE_URL','').startswith('sqlite:////tmp/mylil-multi-'):
    raise RuntimeError('Local QA only')
from backend.api import main
from backend.api.db import SessionLocal
from backend.api.models import Presence,User,Entitlement
from backend.api.mobility import RentalAsset,RentalLease
from backend.api.economy import credit
from sqlalchemy import select
from backend.api.geography import road_segments,traversable
data=json.loads(sys.argv[1]);city=data['city']
routes=[]
for a,b in road_segments(city):
    length=math.dist(a,b)
    if length<30:continue
    v=((b[0]-a[0])/length,(b[1]-a[1])/length)
    if all(traversable(city,a[0]+v[0]*d,a[1]+v[1]*d,'car') for d in range(2,int(length)-1)):
        routes.append((length,a,b,v))
length,a,b,v=max(routes)
x,z=a[0]+v[0]*5,a[1]+v[1]*5
with SessionLocal.begin() as db:
    for id in data.get('users',[]):
        p=db.get(Presence,id);p.x=x;p.z=z;p.mode='walk';p.zone_id='world';p.motion_speed=0;p.last_move=time.time();p.updated_at=time.time()
        if data.get('kind'):
            entitlement=db.get(Entitlement,(id,data['kind']))
            if entitlement:db.delete(entitlement)
            credit(db,id,100,'local_browser_qa','motion:'+str(time.time()),'motion:'+id+':'+str(time.time()),currency='xp')
    asset=None
    if data.get('kind'):
        asset=db.scalar(select(RentalAsset).where(RentalAsset.city==city,RentalAsset.kind==data['kind'],RentalAsset.active_user_id==None))
        asset.x=x;asset.z=z
    if data.get('heading'):
        lease=db.scalar(select(RentalLease).where(RentalLease.user_id==data['users'][0],RentalLease.ended_at==None));lease.heading=math.atan2(v[0],v[1])
print(json.dumps({'x':x,'z':z,'direction':v,'length':length-10,'asset':asset.id if asset else None}))
