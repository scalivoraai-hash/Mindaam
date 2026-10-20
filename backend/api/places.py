import math,time
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select,func
from .geography import district
from .models import User,Presence,Claim,Collectible,Mission,Event
from .auth import current_user
from .db import get_db
from .world import visible
router=APIRouter(prefix='/api/places')
@router.get('/{city}')
def places(city:str,u=Depends(current_user),db=Depends(get_db)):
 d=district(city);own=db.get(Presence,u.id);peers=[];rows=[];objects=list(db.scalars(select(Collectible).where(Collectible.city==city,Collectible.active==True)))
 if own and own.city==city:
  for p,target in db.execute(select(Presence,User).join(User,User.id==Presence.user_id).where(Presence.city==city,Presence.updated_at>time.time()-45,User.suspended==False)):
   if target.id==u.id or visible(db,u,target,p,own):peers.append({'id':target.id,'username':target.username,'x':p.x,'z':p.z})
 for f in d['features']:
  t=f['tags'];p=f['points']
  if not t.get('name') or not any(k in t for k in ['amenity','shop','leisure','tourism','public_transport']):continue
  q=p[:-1] if len(p)>2 and p[0]==p[-1] else p;x=sum(p[0] for p in q)/len(q);z=sum(p[1] for p in q)/len(q)
  rows.append({'id':f['id'],'name':t['name'],'category':t.get('amenity') or t.get('shop') or t.get('leisure') or t.get('tourism') or 'transport','x':x,'z':z,'source':'OpenStreetMap','merchant_verified':False,'online':sum(math.hypot(p['x']-x,p['z']-z)<=60 for p in peers),'collectibles':sum(math.hypot(c.x-x,c.z-z)<=100 for c in objects)})
 return {'district':d.get('district',city),'online':len(peers),'people':peers,'places':rows,'missions':[{'id':m.id,'title':m.title} for m in db.scalars(select(Mission).where(Mission.city==city))],'events':[{'id':e.id,'title':e.title} for e in db.scalars(select(Event).where(Event.city==city,Event.starts_at>time.time()-7200))]}
@router.get('/{city}/leaderboard')
def leaderboard(city:str,period:str='week',u=Depends(current_user),db=Depends(get_db)):
 district(city)
 if period not in ['today','week','month','all']:raise HTTPException(422,'Unknown period')
 seconds={'today':86400,'week':7*86400,'month':30*86400,'all':1e12}[period];rows={}
 for id,name,kind,count in db.execute(select(User.id,User.username,Collectible.kind,func.count(Claim.id)).join(Claim,Claim.user_id==User.id).join(Collectible,Collectible.id==Claim.collectible_id).where(Collectible.city==city,Claim.created_at>time.time()-seconds,User.suspended==False,User.privacy=='City Mode').group_by(User.id,User.username,Collectible.kind)):
  row=rows.setdefault(id,{'id':id,'username':name,'xp':0,'collections':0});row['xp']+=count*(5 if kind=='fruit' else 15);row['collections']+=count
 return {'period':period,'metric':'Collection XP','rows':sorted(rows.values(),key=lambda x:-x['xp'])[:30]}

from .models import Audit
from .core import Strict
from .geography import road_segments
from .world import snapshot
class Travel(Strict):
 city:str
 place_id:str
@router.post('/travel/visit')
def fast_travel(data:Travel,u=Depends(current_user),db=Depends(get_db)):
 from .growth import require_access
 require_access(db,u,data.city)
 if not u.onboarded:raise HTTPException(409,'Complete onboarding first')
 db.scalar(select(User).where(User.id==u.id).with_for_update())
 p=db.get(Presence,u.id)
 from .transit import current
 from .mobility import current as rental_current
 if rental_current(db,u) or current(db,u) or p and p.zone_id!='world':raise HTTPException(409,'Exit your vehicle or venue before travelling')
 recent=db.scalar(select(Audit).where(Audit.actor_id==u.id,Audit.action=='virtual_fast_travel',Audit.created_at>time.time()-30))
 if recent:raise HTTPException(429,'Fast travel is available once every 30 seconds')
 d=district(data.city);f=next((f for f in d['features'] if f['id']==data.place_id and f['tags'].get('name') and any(k in f['tags'] for k in ['amenity','shop','leisure','tourism'])),None)
 if not f:raise HTTPException(404,'Mapped destination unavailable')
 q=f['points'];x=sum(a[0] for a in q)/len(q);z=sum(a[1] for a in q)/len(q)
 candidates=[]
 for a,b in road_segments(data.city):
  dx,dz=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz or 1)));px,pz=a[0]+dx*t,a[1]+dz*t
  if abs(px)<=d['radius'] and abs(pz)<=d['radius']:candidates.append((math.hypot(px-x,pz-z),px,pz))
 if not candidates:raise HTTPException(409,'Destination has no accessible mapped path')
 distance,x,z=min(candidates)
 if distance>200:raise HTTPException(409,'Destination is outside the playable road network')
 p=db.get(Presence,u.id)
 if not p:p=Presence(user_id=u.id);db.add(p)
 p.city=data.city;p.x=x;p.z=z;p.mode='walk';p.updated_at=p.last_move=time.time();u.city=data.city
 db.add(Audit(actor_id=u.id,action='virtual_fast_travel',target=data.city+':'+data.place_id));db.flush()
 return snapshot(db,u,data.city)
