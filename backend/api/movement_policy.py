"""Versioned global speeds. Inputs are intentions; only the server integrates metres."""
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, model_validator, ValidationError
from sqlalchemy import select
from .db import get_db
from .models import Config, Audit
from .core import Strict, serialize
from .operations import super_admin, audit

router=APIRouter(prefix='/api')
KEY='movement_transport_v1'
# Preserve the approved outdoor pace and currently effective vehicle maxima.
DEFAULTS={'walk':2.0,'run':4.6875,'bike':84.0,'ebike':93.0,'scooter':34.0,'car':120.0,'boat':20.0,'swim':3.0}
BOUNDS={'walk':(.5,4),'run':(1,8),'bike':(2,84),'ebike':(2,100),'scooter':(2,45),'car':(5,120),'boat':(1,30),'swim':(.5,5)}
LABELS={'walk':'Avatar walking','run':'Avatar running','bike':'Bicycle','ebike':'Electric bicycle','scooter':'Motorbike / city scooter','car':'Car','boat':'Boat','swim':'Swimming'}

def initial(db):
 values=dict(DEFAULTS)
 legacy=db.get(Config,'rental_types')
 if legacy:
  for kind,cfg in legacy.value.items():
   if kind in values:
    # Previous land vehicle policy imposed these floors on existing settings.
    values[kind]=max(DEFAULTS[kind],float(cfg['speed'])) if kind in ('bike','ebike','scooter','car') else float(cfg['speed'])
 return {'version':0,'speeds':values,'defaults':dict(values),'updated_at':None,'updated_by':None}

def read(db):
 row=db.get(Config,KEY)
 return row.value if row else initial(db)

def bounds(value):
 # Grandfather an existing approved rental maximum without increasing it.
 return {k:(lo,max(hi,value['defaults'][k])) for k,(lo,hi) in BOUNDS.items()}

def public(db):
 value=read(db)
 return {k:value[k] for k in ('version','speeds','updated_at')}

class Speeds(Strict):
 walk:float=Field(ge=.5,le=4,allow_inf_nan=False,strict=True)
 run:float=Field(ge=1,le=8,allow_inf_nan=False,strict=True)
 bike:float=Field(ge=2,le=120,allow_inf_nan=False,strict=True)
 ebike:float=Field(ge=2,le=120,allow_inf_nan=False,strict=True)
 scooter:float=Field(ge=2,le=120,allow_inf_nan=False,strict=True)
 car:float=Field(ge=5,le=120,allow_inf_nan=False,strict=True)
 boat:float=Field(ge=1,le=120,allow_inf_nan=False,strict=True)
 swim:float=Field(ge=.5,le=120,allow_inf_nan=False,strict=True)
 @model_validator(mode='after')
 def ordered(self):
  if self.walk>=self.run:raise ValueError('Walking must be slower than running')
  return self

class Update(Strict):
 expected_version:int=Field(ge=0)
 speeds:Speeds
 reason:str=Field(min_length=12,max_length=500)

class Restore(Strict):
 expected_version:int=Field(ge=0)
 version:int|None=Field(default=None,ge=1)
 reason:str=Field(min_length=12,max_length=500)

def save(db,u,speeds,expected,reason,restored=None):
 # Insert-on-conflict also serializes the very first concurrent save. No new table.
 dialect=db.bind.dialect.name
 if dialect=='postgresql':from sqlalchemy.dialects.postgresql import insert
 else:from sqlalchemy.dialects.sqlite import insert
 db.execute(insert(Config).values(key=KEY,value=initial(db),updated_at=time.time()).on_conflict_do_nothing(index_elements=['key']))
 row=db.scalar(select(Config).where(Config.key==KEY).with_for_update().execution_options(populate_existing=True))
 before=row.value
 if before['version']!=expected:raise HTTPException(409,'Settings changed. Refresh and review the current version before saving.')
 if len(reason.strip())<12:raise HTTPException(422,'Document the reason for this change')
 try:values=Speeds.model_validate(speeds).model_dump()
 except ValidationError:raise HTTPException(422,'Movement speeds are outside approved limits')
 if any(not lo<=values[k]<=hi for k,(lo,hi) in bounds(before).items()):raise HTTPException(422,'Movement speeds are outside approved limits')
 value={**before,'version':before['version']+1,'speeds':values,'updated_at':time.time(),'updated_by':u.username}
 row.value=value;row.updated_at=value['updated_at']
 audit(db,u,'movement.settings_updated',KEY,{'old':before['speeds'],'new':values,'version':value['version'],'previous_version':before['version'],'reason':reason.strip(),'restored_version':restored})
 db.flush()
 return value

@router.get('/movement/config')
def public_config(db=Depends(get_db)):return public(db)

@router.get('/super-admin/movement')
def admin_config(u=Depends(super_admin),db=Depends(get_db)):
 return {**read(db),'bounds':bounds(read(db)),'labels':LABELS,'history':[serialize(a) for a in db.scalars(select(Audit).where(Audit.action=='movement.settings_updated',Audit.target==KEY).order_by(Audit.created_at.desc()).limit(100))]}

@router.put('/super-admin/movement')
def update(data:Update,u=Depends(super_admin),db=Depends(get_db)):
 return save(db,u,data.speeds.model_dump(),data.expected_version,data.reason)

@router.post('/super-admin/movement/restore')
def restore(data:Restore,u=Depends(super_admin),db=Depends(get_db)):
 values=read(db)['defaults']
 if data.version is not None:
  rows=db.scalars(select(Audit).where(Audit.action=='movement.settings_updated',Audit.target==KEY).order_by(Audit.created_at.desc()).limit(100))
  entry=next((a for a in rows if a.details.get('version')==data.version),None)
  if not entry:raise HTTPException(404,'Saved configuration version unavailable')
  values=entry.details['new']
 return save(db,u,values,data.expected_version,data.reason,data.version or 'defaults')
