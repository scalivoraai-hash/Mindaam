"""Bounded hourly opportunities. Unclaimed rotations are deterministic, not DB rows.

An instance is materialised only after authoritative proximity validation; its old
claim and ledger entries then remain immutable. Existing authored items are intact.
"""
import hashlib,time
from uuid import uuid5,NAMESPACE_URL
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import select,func
from .db import get_db
from .core import Strict
from .models import Collectible,Claim,Config,Audit,User
from .economy import config
from .operations import super_admin
from .world_content import prepared_points
from .expansion import Destination
router=APIRouter(prefix='/api')
DEFAULTS={'enabled':True,'density':16,'refresh_minutes':60,'daily_limit':96,'minimum_claim_seconds':.4}
class Settings(Strict):
 enabled:bool=True
 density:int=Field(default=16,ge=4,le=16,strict=True)
 refresh_minutes:int=Field(default=60,ge=30,le=360,strict=True)
 daily_limit:int=Field(default=96,ge=12,le=200,strict=True)
 minimum_claim_seconds:float=Field(default=.4,ge=.2,le=5,allow_inf_nan=False)

def settings(db):return Settings(**config(db,'collectible_rotation',DEFAULTS)).model_dump()

from functools import lru_cache
@lru_cache(maxsize=64)
def rotation_points(city):
 import json
 from pathlib import Path
 root=Path(__file__).resolve().parents[1]/'data'
 path=root/'exploration-rotation-points.json'
 item=json.loads(path.read_text()).get(city,{}) if path.exists() else {}
 if item.get('map_sha256')==hashlib.sha256((root/(city+'.json.gz')).read_bytes()).hexdigest():
  return item['points'][:96]
 return prepared_points(city,48)

def wave(db,city,now=None):
 state=settings(db)
 if not state['enabled']:return []
 d=db.get(Destination,city)
 if not d or d.status!='ACTIVE' or not d.public or not d.joinable:return []
 now=time.time() if now is None else now
 interval=state['refresh_minutes']*60;cycle=int(now//interval);points=rotation_points(city);count=min(state['density'],len(points)//2)
 offset=int(hashlib.sha256(city.encode()).hexdigest()[:8],16)%len(points)
 kinds=[('fruit','Apple'),('fruit','Orange'),('fruit','Bananas'),('gem','Gem'),('gem','Crystal'),('treasure','Treasure')]
 result=[]
 for index in range(count):
  x,z=points[(offset+cycle*count+index)%len(points)];kind,title=kinds[(cycle+index)%len(kinds)]
  key=f'mindaam:rotation:v2:{city}:{interval}:{cycle}:{index}'
  result.append(Collectible(id=str(uuid5(NAMESPACE_URL,key)),city=city,title=title,kind=kind,x=x,z=z,active=True,starts_at=cycle*interval,ends_at=(cycle+1)*interval,max_claims=100000,claims=0,origin="rotation"))
 return result

def visible(db,u,city,objects):
 generated=wave(db,city)
 if not generated:return [c for c in objects if c.origin!='rotation']
 ids=[c.id for c in generated]
 objects=[c for c in objects if c.origin!='rotation' or c.id in ids]
 claimed=set(db.scalars(select(Claim.collectible_id).where(Claim.user_id==u.id,Claim.collectible_id.in_(ids))))
 existing={c.id for c in objects}
 persisted=set(db.scalars(select(Collectible.id).where(Collectible.id.in_(ids))))
 # Only a participant's existing claim hides their item; another user's claim
 # must not create duplicate representations of a generated instance.
 return objects+[c for c in generated if c.id not in existing and c.id not in claimed and c.id not in persisted]

def materialize(db,object_id,p):
 if not p or p.zone_id!='world' or p.updated_at<time.time()-45:return None
 candidates=wave(db,p.city)
 c=next((c for c in candidates if c.id==object_id),None)
 if not c:return None
 import math
 if math.hypot(p.x-c.x,p.z-c.z)>5:raise HTTPException(409,'Move closer to collect this item')
 # City lock serialises first materialisation for two genuinely nearby users.
 db.scalar(select(Destination.id).where(Destination.id==p.city).with_for_update())
 existing=db.get(Collectible,object_id)
 if existing:return existing
 db.add(c);db.flush();return c

def guard(db,u,c):
 if c.origin!='rotation':return
 if not any(item.id==c.id for item in wave(db,c.city)):raise HTTPException(409,'This exploration trail has refreshed. Look for a new item.')
 state=settings(db);now=time.time()
 recent=db.scalar(select(func.max(Claim.created_at)).where(Claim.user_id==u.id))
 if recent and now-recent<state['minimum_claim_seconds']:raise HTTPException(429,'Take a moment before collecting another item')
 # Counts every claim, so switching worlds/tabs cannot reset the daily allowance.
 count=db.scalar(select(func.count()).select_from(Claim).where(Claim.user_id==u.id,Claim.created_at>=int(now//86400)*86400))
 if count>=state['daily_limit']:raise HTTPException(429,'You have collected today’s exploration allowance. New rewards return tomorrow.')

@router.get('/super-admin/collectibles')
def admin_read(u=Depends(super_admin),db=Depends(get_db)):return settings(db)
@router.put('/super-admin/collectibles')
def admin_save(data:Settings,u=Depends(super_admin),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 row=db.get(Config,'collectible_rotation')
 if not row:row=Config(key='collectible_rotation');db.add(row)
 row.value=data.model_dump();db.add(Audit(actor_id=u.id,action='collectibles.rotation_configured',target='collectible_rotation',details=row.value));return row.value
