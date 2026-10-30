"""Authenticated product feedback with private, audited owner review."""
import time
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, field_validator
from sqlalchemy import String, Text, Float, ForeignKey, select, func
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, get_db
from .models import User, Audit
from .auth import current_user
from .operations import super_admin
from .core import Strict, serialize

router=APIRouter(prefix='/api')
Category=Literal['feature','feedback']
Status=Literal['new','reviewing','planned','completed','declined']
class ProductFeedback(Base):
 __tablename__='product_feedback'
 id:Mapped[str]=mapped_column(String(36),primary_key=True)
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 category:Mapped[str]=mapped_column(String(20),index=True)
 title:Mapped[str]=mapped_column(String(120))
 description:Mapped[str]=mapped_column(Text)
 status:Mapped[str]=mapped_column(String(20),default='new',index=True)
 internal_notes:Mapped[str]=mapped_column(Text,default='')
 created_at:Mapped[float]=mapped_column(Float,default=time.time,index=True)
 updated_at:Mapped[float]=mapped_column(Float,default=time.time)
class Submission(Strict):
 request_id:UUID
 category:Category
 title:str=Field(min_length=3,max_length=120)
 description:str=Field(min_length=10,max_length=4000)
 @field_validator('title','description',mode='before')
 @classmethod
 def trim(cls,value):return value.strip() if isinstance(value,str) else value

@router.post('/feedback',status_code=201)
def submit(data:Submission,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 old=db.get(ProductFeedback,str(data.request_id))
 if old:
  if old.user_id!=u.id or any(getattr(old,k)!=getattr(data,k) for k in ['category','title','description']):raise HTTPException(409,'Submission ID conflict')
  return {'id':old.id,'status':old.status}
 count=db.scalar(select(func.count()).select_from(ProductFeedback).where(ProductFeedback.user_id==u.id,ProductFeedback.created_at>time.time()-3600))
 if count>=3:raise HTTPException(429,'Your submissions are saved. Please wait before sending another.')
 row=ProductFeedback(id=str(data.request_id),user_id=u.id,**data.model_dump(exclude={'request_id'}));db.add(row);db.flush()
 db.add(Audit(actor_id=u.id,action='feedback.submitted',target=row.id,details={'category':row.category}))
 return {'id':row.id,'status':row.status}

@router.get('/super-admin/feedback')
def review_list(category:Category|None=None,status:Status|None=None,q:str=Query('',max_length=120),offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),u=Depends(super_admin),db=Depends(get_db)):
 filters=[]
 if category:filters.append(ProductFeedback.category==category)
 if status:filters.append(ProductFeedback.status==status)
 if q.strip():filters.append(ProductFeedback.title.ilike('%'+q.strip()+'%')|ProductFeedback.description.ilike('%'+q.strip()+'%'))
 total=db.scalar(select(func.count()).select_from(ProductFeedback).where(*filters))
 return {'items':[serialize(r) for r in db.scalars(select(ProductFeedback).where(*filters).order_by(ProductFeedback.created_at.desc(),ProductFeedback.id).offset(offset).limit(limit))],'total':total,'offset':offset,'limit':limit}
class Review(Strict):
 status:Status
 internal_notes:str=Field(default='',max_length=4000)
@router.patch('/super-admin/feedback/{id}')
def review(id:str,data:Review,u=Depends(super_admin),db=Depends(get_db)):
 row=db.scalar(select(ProductFeedback).where(ProductFeedback.id==id).with_for_update())
 if not row:raise HTTPException(404,'Submission unavailable')
 previous=row.status;row.status=data.status;row.internal_notes=data.internal_notes.strip();row.updated_at=time.time()
 db.add(Audit(actor_id=u.id,action='feedback.reviewed',target=id,details={'from':previous,'to':row.status,'notes_changed':True}))
 return serialize(row)
