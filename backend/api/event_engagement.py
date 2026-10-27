"""Bounded polls and moderated Q&A inside existing locked Event records."""
import time
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field,field_validator
from .auth import current_user
from .db import get_db
from .core import Strict
from .models import Attendee,Audit,uid
router=APIRouter(prefix='/api/events')

def joined(db,e,user):
 from .event_tickets import require_ticket
 a=db.get(Attendee,(e.id,user.id))
 if e.status!='live' or not a or a.state!='active':raise HTTPException(403,'Join the live event first')
 require_ticket(db,e,user)

def summary(e,user_id,moderator):
 state=e.programme or {}
 return {'polls':[{'id':p['id'],'question':p['question'],'options':p['options'],'closed':p.get('closed',False),'counts':[sum(v==i for v in p.get('votes',{}).values()) for i in range(len(p['options']))],'my_vote':p.get('votes',{}).get(user_id)} for p in state.get('polls',[])],
 'questions':[{k:q.get(k) for k in ['id','body','name','answer','hidden']} for q in state.get('questions',[]) if moderator or not q.get('hidden')]}

class PollInput(Strict):
 question:str=Field(min_length=3,max_length=200)
 options:list[str]=Field(min_length=2,max_length=6)
 @field_validator('options')
 @classmethod
 def valid_options(cls,values):
  values=[v.strip() for v in values]
  if any(not v or len(v)>100 for v in values) or len(set(values))!=len(values):raise ValueError('Use distinct, nonempty options up to 100 characters')
  return values

@router.post('/{id}/polls')
def poll(id:str,data:PollInput,u=Depends(current_user),db=Depends(get_db)):
 from .events import get
 e=get(db,id,u,True);joined(db,e,u);state=dict(e.programme or {});polls=list(state.get('polls',[]))
 if len(polls)>=10:raise HTTPException(409,'An event can contain at most ten polls')
 p={'id':uid(),**data.model_dump(),'votes':{},'closed':False};polls.append(p);state['polls']=polls;e.programme=state
 db.add(Audit(actor_id=u.id,action='event.poll_created',target=id,details={'poll_id':p['id']}));return summary(e,u.id,True)

class Vote(Strict):
 option:int=Field(ge=0,le=5,strict=True)

@router.post('/{id}/polls/{poll_id}/vote')
def vote(id:str,poll_id:str,data:Vote,u=Depends(current_user),db=Depends(get_db)):
 from .events import get,host
 e=get(db,id,u);joined(db,e,u);state=dict(e.programme or {});polls=[dict(p) for p in state.get('polls',[])];p=next((p for p in polls if p['id']==poll_id),None)
 if not p or p.get('closed'):raise HTTPException(409,'This poll is closed or unavailable')
 if data.option>=len(p['options']):raise HTTPException(422,'Choose an available option')
 p['votes']={**p.get('votes',{}),u.id:data.option};state['polls']=polls;e.programme=state
 return summary(e,u.id,host(db,e,u))

@router.post('/{id}/polls/{poll_id}/close')
def close_poll(id:str,poll_id:str,u=Depends(current_user),db=Depends(get_db)):
 from .events import get
 e=get(db,id,u,True);state=dict(e.programme or {});polls=[dict(p) for p in state.get('polls',[])];p=next((p for p in polls if p['id']==poll_id),None)
 if not p:raise HTTPException(404,'Poll unavailable')
 p['closed']=True;state['polls']=polls;e.programme=state;return summary(e,u.id,True)

class Question(Strict):
 body:str=Field(min_length=3,max_length=300)

@router.post('/{id}/questions')
def question(id:str,data:Question,u=Depends(current_user),db=Depends(get_db)):
 from .events import get,host
 e=get(db,id,u);joined(db,e,u);state=dict(e.programme or {});questions=list(state.get('questions',[]));now=time.time()
 if len(questions)>=100 or sum(q['user_id']==u.id and q['created_at']>now-60 for q in questions)>=3:raise HTTPException(429,'Please allow time for the current questions')
 questions.append({'id':uid(),'user_id':u.id,'name':u.username,'body':data.body,'created_at':now,'answer':'','hidden':False});state['questions']=questions;e.programme=state
 return summary(e,u.id,host(db,e,u))

class Answer(Strict):
 answer:str=Field(default='',max_length=1000)
 hidden:bool=False

@router.put('/{id}/questions/{question_id}')
def answer(id:str,question_id:str,data:Answer,u=Depends(current_user),db=Depends(get_db)):
 from .events import get
 e=get(db,id,u,True);state=dict(e.programme or {});questions=[dict(q) for q in state.get('questions',[])];q=next((q for q in questions if q['id']==question_id),None)
 if not q:raise HTTPException(404,'Question unavailable')
 q.update(data.model_dump());state['questions']=questions;e.programme=state
 db.add(Audit(actor_id=u.id,action='event.question_moderated',target=id,details={'question_id':question_id,'hidden':data.hidden}));return summary(e,u.id,True)
