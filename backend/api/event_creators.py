"""Creator discovery and explicitly authorised image highlights; no recording service."""
import time
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import select,func
from .core import Strict
from .auth import current_user
from .db import get_db
from .models import Event,User,Attendee,Audit,uid
from . import events
router=APIRouter(prefix='/api')

@router.get('/creators/{user_id}')
def profile(user_id:str,u=Depends(current_user),db=Depends(get_db)):
 from .world import blocked
 person=db.get(User,user_id)
 if not person or person.suspended or blocked(db,u.id,user_id):raise HTTPException(404,'Creator unavailable')
 public=list(db.scalars(select(Event).where(Event.host_id==user_id,Event.visibility=='public',Event.status.in_(['scheduled','live','ended'])).order_by(Event.starts_at.desc()).limit(30)))
 # Counts reflect persisted participations, never ambient NPCs or fabricated reach.
 rows=[{'id':e.id,'title':e.title,'city':e.city,'starts_at':e.starts_at,'status':e.status,'ticket_price':e.ticket_price,'cover_image':(e.programme or {}).get('cover_image',''),'highlights':(e.programme or {}).get('highlights',[])} for e in public if events.visible(db,e,u)]
 return {'id':person.id,'name':person.username,'events':rows,'public_events':db.scalar(select(func.count()).select_from(Event).where(Event.host_id==user_id,Event.visibility=='public',Event.status.in_(['scheduled','live','ended']))) or 0}

class Highlight(Strict):
 title:str=Field(min_length=3,max_length=100)
 image_url:str=Field(max_length=500,pattern=r'^(https://[^\s]+|/uploads/[^\s]+)$')
 rights_confirmed:bool
 participants_consented:bool

@router.post('/events/{id}/highlights',status_code=201)
def add(id:str,data:Highlight,u=Depends(current_user),db=Depends(get_db)):
 e=events.get(db,id,u,True)
 if e.host_id!=u.id:raise HTTPException(403,'Only the organiser can publish highlights')
 if e.status not in ['live','ended']:raise HTTPException(409,'Highlights are available during or after the event')
 if not data.rights_confirmed or not data.participants_consented:raise HTTPException(422,'Confirm content rights and consent from everyone depicted')
 state=dict(e.programme or {});items=list(state.get('highlights',[]))
 if len(items)>=12:raise HTTPException(409,'An event can have up to twelve highlights')
 row={'id':uid(),'title':data.title,'image_url':data.image_url,'published_at':time.time()};items.append(row);state['highlights']=items;e.programme=state
 db.add(Audit(actor_id=u.id,action='event.highlight_authorised',target=id,details={**row,'rights_confirmed':True,'participants_consented':True}));return row

@router.delete('/events/{id}/highlights/{highlight_id}')
def remove(id:str,highlight_id:str,u=Depends(current_user),db=Depends(get_db)):
 e=events.get(db,id,u,True)
 if e.host_id!=u.id:raise HTTPException(403,'Only the organiser can remove highlights')
 state=dict(e.programme or {});state['highlights']=[h for h in state.get('highlights',[]) if h['id']!=highlight_id];e.programme=state
 db.add(Audit(actor_id=u.id,action='event.highlight_removed',target=id,details={'highlight_id':highlight_id}));return {'ok':True}
