"""Admin-configured consumer packs reuse the existing Stripe checkout and webhook."""
import os
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import select
from .auth import current_user
from .db import get_db
from .models import Config,Audit,User
from .core import Strict
from .economy import config
from .operations import super_admin
router=APIRouter(prefix='/api')
DEFAULT_PACKS={
 'credits_starter':{'amount':199,'credits':200,'name':'Starter'},
 'credits_explorer':{'amount':499,'credits':550,'name':'Explorer'},
 'credits_adventurer':{'amount':999,'credits':1200,'name':'Adventurer'},
 'credits_world_pass':{'amount':1999,'credits':2600,'name':'World Pass'},
 'credits_power_user':{'amount':4999,'credits':7000,'name':'Power User'},
}
def catalogue(db):
 from .commerce import SKUS
 return config(db,'commerce_catalog',{**DEFAULT_PACKS,**(SKUS if os.getenv('APP_ENV','local') in ['local','test'] else {})})

def public(db):
 return [{'id':id,'name':p['name'],'credits':p['credits'],'amount_pence':p['amount'],'currency':'GBP'} for id,p in catalogue(db).items() if id.startswith('credits_')]

@router.get('/payments/credits')
def packs(u=Depends(current_user),db=Depends(get_db)):
 from .payment_settlement import configured,summary
 return {'packs':public(db),'ready':configured(),'payment_review':summary(db,u.id)}

class Pack(Strict):
 id:str=Field(pattern=r'^credits_[a-z0-9_]{1,50}$')
 name:str=Field(min_length=2,max_length=100)
 amount_pence:int=Field(ge=1,le=10000000,strict=True)
 credits:int=Field(ge=1,le=1000000,strict=True)
class Packs(Strict):
 packs:list[Pack]=Field(min_length=1,max_length=20)

@router.get('/super-admin/credit-packs')
def admin_read(u=Depends(super_admin),db=Depends(get_db)):
 return packs(u,db)

@router.put('/super-admin/credit-packs')
def admin_save(data:Packs,u=Depends(super_admin),db=Depends(get_db)):
 if len({p.id for p in data.packs})!=len(data.packs):raise HTTPException(422,'Use a unique ID for each Credit pack')
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 row=db.scalar(select(Config).where(Config.key=='commerce_catalog').with_for_update())
 # Merchant products and any unrelated catalogue entries are preserved exactly.
 values={id:p for id,p in catalogue(db).items() if not id.startswith('credits_')}
 values.update({p.id:{'name':p.name,'amount':p.amount_pence,'credits':p.credits} for p in data.packs})
 if not row:row=Config(key='commerce_catalog');db.add(row)
 row.value=values;db.add(Audit(actor_id=u.id,action='credit_packs.updated',target='commerce_catalog',details={'pack_ids':[p.id for p in data.packs]}));return {'packs':public(db)}
