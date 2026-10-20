"""Explicitly local fixtures for real-browser acceptance, never a production route."""
import os,sys,json,time,math,wave,struct
from pathlib import Path
if os.environ.get('APP_ENV')!='local' or not os.environ.get('DATABASE_URL','').startswith('sqlite:////tmp/mylil-multi-'):
    raise RuntimeError('This fixture is restricted to disposable local QA databases')
from backend.api import main
from backend.api.db import Base,engine,SessionLocal
from backend.api.models import Presence,User
from backend.api.mobility import RentalAsset
from backend.api.transit import Route,hub,boarding_stop
from backend.api.economy import credit
from backend.api.geography import road_segments,nearest_safe_position,traversable,safe_spawn
from sqlalchemy import select
action=sys.argv[1]
if action=='init':
    Base.metadata.create_all(engine)
    from backend.api.cli import seed
    with SessionLocal.begin() as db:seed(db)
    with wave.open('/tmp/mylil-test-tone.wav','wb') as w:
        w.setparams((1,2,48000,0,'NONE','not compressed'))
        w.writeframes(b''.join(struct.pack('<h',int(5000*math.sin(2*math.pi*440*i/48000))) for i in range(48000)))
    print('{}')
else:
    data=json.loads(sys.argv[2])
    with SessionLocal.begin() as db:
        city=data['city'];users=[db.get(User,id) for id in data['users']]
        if action=='place':
            kind=data.get('kind')
            if kind:
                assets=list(db.scalars(select(RentalAsset).where(RentalAsset.city==city,RentalAsset.kind==kind,RentalAsset.enabled==True)))
                asset=next(a for a in assets if traversable(city,a.x,a.z,'car' if kind=='car' else 'walk'))
                x,z=asset.x,asset.z
            else:
                x,z=safe_spawn(city)
            for i,u in enumerate(users):
                p=db.get(Presence,u.id);p.city=city;p.x=x;p.z=z;p.zone_id='world';p.mode='walk';p.motion_speed=0;p.last_move=time.time();p.updated_at=time.time()
                credit(db,u.id,100,'local_browser_qa','local-only-'+str(time.time()),'local-qa:'+u.id+':'+str(time.time()))
                credit(db,u.id,100,'local_browser_qa','xp-local-only-'+str(time.time()),'xp-local-qa:'+u.id+':'+str(time.time()),currency='xp')
            directions=[(math.sin(i*math.pi/8),math.cos(i*math.pi/8)) for i in range(16)]
            direction=max(directions,key=lambda v:sum(traversable(city,x+v[0]*d,z+v[1]*d,'walk') for d in [j*.25 for j in range(1,33)]))
            print(json.dumps({'x':x,'z':z,'direction':direction,'asset':asset.id if kind else None}))
        elif action=='bus':
            route=db.scalar(select(Route).where(Route.origin==city,Route.enabled==True))
            if route is None:raise ValueError('No existing enabled bus route for '+city)
            # An explicit local timetable fixture opens the normal validated boarding window.
            route.frequency=120;route.number=str(101+int(time.time()%120)//30);route.duration=40
            for u in users:
                p=db.get(Presence,u.id);h=hub(city);p.x=h['x'];p.z=h['z'];p.mode='walk';p.zone_id='world';p.last_move=time.time();p.updated_at=time.time()
            print(json.dumps({'route':route.id,'destination':route.destination}))
