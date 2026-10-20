"""Catalogued gifts debit the existing immutable wallet; never transfer Credits P2P."""
import time
from uuid import UUID
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import String,Integer,Float,ForeignKey,select,func
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base,get_db
from .models import User,MediaSession,Event,Attendee,Config,uid
from .auth import current_user
from .core import Strict,serialize
from .economy import config,credit,balance
from .operations import super_admin,audit
from .world import blocked
router=APIRouter(prefix='/api')
DEFAULTS={k:{'name':name,'icon':icon,'price':price,'enabled':True,'category':'Social','animation':'float'} for k,name,icon,price in [('rose','Rose','🌹',1),('coffee','Coffee','☕',3),('heart','Heart','❤️',5),('crystal','Crystal','💎',10),('crown','Crown','👑',20),('supernova','Supernova','🚀',50)]}
class GiftDelivery(Base):
 __tablename__='gift_deliveries'
 id:Mapped[str]=mapped_column(String(36),primary_key=True)
 sender_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 recipient_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 context_type:Mapped[str]=mapped_column(String(20))
 context_id:Mapped[str]=mapped_column(String(36),index=True)
 gift_id:Mapped[str]=mapped_column(String(40))
 gift_name:Mapped[str]=mapped_column(String(80))
 icon:Mapped[str]=mapped_column(String(30))
 price:Mapped[int]=mapped_column(Integer)
 ledger_id:Mapped[str]=mapped_column(ForeignKey('wallet_transactions.id'))
 created_at:Mapped[float]=mapped_column(Float,default=time.time)
class Reaction(Base):
 __tablename__='social_reactions'
 id:Mapped[str]=mapped_column(String(36),primary_key=True)
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 context_type:Mapped[str]=mapped_column(String(20))
 context_id:Mapped[str]=mapped_column(String(36),index=True)
 emoji:Mapped[str]=mapped_column(String(30))
 created_at:Mapped[float]=mapped_column(Float,default=time.time)

def catalogue(db):return config(db,'social_gifts',DEFAULTS)
def eligible(db,u,kind,id):
 if kind=='event':
  from .events import get
  e=get(db,id,u);a=db.get(Attendee,(id,u.id))
  if e.status!='live' or not a or a.state!='active':raise HTTPException(403,'Join this live event first')
  ids=list(db.scalars(select(Attendee.user_id).where(Attendee.event_id==id,Attendee.state=='active')))
 elif kind=='conversation':
  from .talk import member
  from .conversations import members,root
  s=member(db,u,id,True)
  if s.event_id:return eligible(db,u,'event',s.event_id)
  s=root(db,s);ids=[m.user_id for m in members(db,s)];id=s.id
 else:raise HTTPException(422,'Unsupported social context')
 users=list(db.scalars(select(User).where(User.id.in_(ids),User.suspended==False)))
 return kind,id,[p for p in users if p.id==u.id or not blocked(db,u.id,p.id)]
class Context(Strict):
 context_type:Literal['conversation','event']
 context_id:str=Field(min_length=1,max_length=36)
class Send(Context):
 id:UUID
 recipient_id:str=Field(min_length=1,max_length=36)
 gift_id:str=Field(min_length=1,max_length=40)
 expected_cost:int=Field(ge=1)
@router.post('/gifts/send')
def send(data:Send,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 old=db.get(GiftDelivery,str(data.id))
 if old:
  if old.sender_id!=u.id or old.recipient_id!=data.recipient_id or old.gift_id!=data.gift_id or old.price!=data.expected_cost:raise HTTPException(409,'Gift request ID already used')
  # A retry after the session ended still returns the original receipt.
  candidate=db.get(MediaSession,data.context_id) if data.context_type=='conversation' else None
  canonical=candidate.event_id or candidate.conversation_id or candidate.id if candidate else data.context_id
  if canonical!=old.context_id:raise HTTPException(409,'Gift request belongs to a different context')
  return {'gift':serialize(old),'credits':balance(db,u.id),'duplicate':True}
 kind,id,people=eligible(db,u,data.context_type,data.context_id)
 if data.recipient_id==u.id or data.recipient_id not in {p.id for p in people}:raise HTTPException(403,'Select an eligible participant other than yourself')
 gift=catalogue(db).get(data.gift_id)
 if not gift or not gift['enabled']:raise HTTPException(409,'Gift unavailable')
 if gift['price']!=data.expected_cost:raise HTTPException(409,'Gift price changed. Review it before sending.')
 tx=credit(db,u.id,-gift['price'],'social_gift',id,'social-gift:'+str(data.id))
 row=GiftDelivery(id=str(data.id),sender_id=u.id,recipient_id=data.recipient_id,context_type=kind,context_id=id,gift_id=data.gift_id,gift_name=gift['name'],icon=gift['icon'],price=gift['price'],ledger_id=tx.id);db.add(row);db.flush()
 return {'gift':serialize(row),'credits':balance(db,u.id),'duplicate':False}
class React(Context):
 id:UUID
 emoji:Literal['👏','❤️','🔥','😂','👍','🎉']
@router.post('/reactions')
def react(data:React,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update());kind,id,people=eligible(db,u,data.context_type,data.context_id)
 old=db.get(Reaction,str(data.id))
 if old:
  if old.user_id!=u.id or old.context_id!=id or old.context_type!=kind or old.emoji!=data.emoji:raise HTTPException(409,'Reaction ID already used')
  return {'ok':True}
 if db.scalar(select(func.count()).select_from(Reaction).where(Reaction.user_id==u.id,Reaction.created_at>time.time()-10))>=4:raise HTTPException(429,'Give other people a moment to react')
 db.add(Reaction(id=str(data.id),user_id=u.id,context_type=kind,context_id=id,emoji=data.emoji));return {'ok':True}
@router.get('/social-activity/{kind}/{id}')
def activity(kind:str,id:str,u=Depends(current_user),db=Depends(get_db)):
 kind,id,people=eligible(db,u,kind,id);names={p.id:p.username for p in people}
 gifts=list(db.scalars(select(GiftDelivery).where(GiftDelivery.context_type==kind,GiftDelivery.context_id==id,GiftDelivery.created_at>time.time()-15,GiftDelivery.sender_id.in_(names),GiftDelivery.recipient_id.in_(names)).order_by(GiftDelivery.created_at.desc()).limit(20)))
 return {'catalogue':{k:v for k,v in catalogue(db).items() if v['enabled']},'recipients':[{'id':p.id,'username':p.username} for p in people if p.id!=u.id],'gifts':[{**serialize(g),'sender':names[g.sender_id],'recipient':names[g.recipient_id]} for g in gifts],'reactions':[serialize(r) for r in db.scalars(select(Reaction).where(Reaction.context_type==kind,Reaction.context_id==id,Reaction.created_at>time.time()-8,Reaction.user_id.in_(names)).limit(30))]}
@router.get('/super-admin/gifts')
def admin_catalogue(u=Depends(super_admin),db=Depends(get_db)):
 return {'catalogue':catalogue(db),'sent':db.scalar(select(func.count()).select_from(GiftDelivery)),'credits_spent':db.scalar(select(func.coalesce(func.sum(GiftDelivery.price),0)))}
class GiftInput(Strict):
 name:str=Field(min_length=2,max_length=80)
 icon:str=Field(min_length=1,max_length=30)
 price:int=Field(ge=1,le=100000)
 enabled:bool=True
 category:str=Field(default='Social',max_length=60)
 animation:Literal['float','sparkle']='float'
@router.put('/super-admin/gifts/{id}')
def edit(id:str,data:GiftInput,u=Depends(super_admin),db=Depends(get_db)):
 import re
 if not re.fullmatch('[a-z0-9_-]{1,40}',id):raise HTTPException(422,'Use a short gift identifier')
 db.scalar(select(User.id).where(User.id==u.id).with_for_update());row=db.scalar(select(Config).where(Config.key=='social_gifts').with_for_update());value=dict(row.value if row else DEFAULTS);value[id]=data.model_dump()
 if row:row.value=value
 else:db.add(Config(key='social_gifts',value=value))
 audit(db,u,'gift.catalogue_updated',id,data.model_dump());return value[id]
