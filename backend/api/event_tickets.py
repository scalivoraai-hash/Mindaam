"""Atomic event entitlements using existing Credits. No creator cash-out or transfers."""
import time
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import String,Integer,Float,ForeignKey,UniqueConstraint,select,func
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base,get_db
from .models import Event,Attendee,User,uid,Audit
from .auth import current_user
from .core import Strict,serialize
from .economy import credit

router=APIRouter(prefix='/api/events')
class EventTicket(Base):
 __tablename__='event_tickets'
 id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
 event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 request_id:Mapped[str]=mapped_column(String(36))
 cost:Mapped[int]=mapped_column(Integer)
 ledger_id:Mapped[str]=mapped_column(ForeignKey('wallet_transactions.id'))
 refunded_at:Mapped[float|None]=mapped_column(Float,nullable=True)
 created_at:Mapped[float]=mapped_column(Float,default=time.time)
 __table_args__=(UniqueConstraint('event_id','user_id'),UniqueConstraint('user_id','request_id'))

def ticket(db,event_id,user_id):return db.scalar(select(EventTicket).where(EventTicket.event_id==event_id,EventTicket.user_id==user_id))
def entitled(db,event,user):
 from .events import host
 if not event.ticket_price or host(db,event,user):return True
 row=ticket(db,event.id,user.id)
 return bool(row and row.refunded_at is None)
def require_ticket(db,event,user):
 if not entitled(db,event,user):raise HTTPException(402,'Purchase a confirmed event ticket before joining')
def sales(db,event_id):return db.scalar(select(func.count()).select_from(EventTicket).where(EventTicket.event_id==event_id,EventTicket.refunded_at==None)) or 0

class Purchase(Strict):
 request_id:UUID
 expected_cost:int=Field(ge=1,le=1000000,strict=True)

@router.post('/{id}/tickets')
def purchase(id:str,data:Purchase,u=Depends(current_user),db=Depends(get_db)):
 from . import events
 from .payment_policy import require_payment_actions
 require_payment_actions()
 e=events.get(db,id,u);db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 prior=db.scalar(select(EventTicket).where(EventTicket.user_id==u.id,EventTicket.request_id==str(data.request_id)))
 if prior:
  if prior.event_id!=id or prior.cost!=data.expected_cost:raise HTTPException(409,'This confirmation belongs to a different ticket')
  return serialize(prior)
 existing=ticket(db,id,u.id)
 if existing:
  if existing.refunded_at is not None:raise HTTPException(409,'This ticket was refunded')
  return serialize(existing)
 if e.status not in ['scheduled','live'] or not e.ticket_price or events.host(db,e,u):raise HTTPException(409,'Tickets are not available for this event')
 if e.ends_at and e.ends_at<=time.time():raise HTTPException(409,'This event has ended')
 from .venue_modes import mode
 if mode(db,e)=='grand_arena':
  from .venue_rentals import booking
  if not booking(db,e.id):raise HTTPException(409,'The organiser must confirm the arena reservation before selling tickets')
 a=events.eligible(db,e,u)
 if e.visibility=='private' and (not a or a.state not in ['approved','active']):raise HTTPException(403,'Obtain the host’s approval before buying a private ticket')
 from .growth import require_access
 require_access(db,u,e.city)
 if e.ticket_price!=data.expected_cost:raise HTTPException(409,'Ticket price changed. Review the new price before confirming')
 if sales(db,id)>=e.capacity-1:raise HTTPException(409,'All audience tickets have been sold')
 row=EventTicket(id=uid(),event_id=id,user_id=u.id,request_id=str(data.request_id),cost=e.ticket_price)
 row.ledger_id=credit(db,u.id,-e.ticket_price,'event_ticket',row.id,'event-ticket:'+str(data.request_id)).id
 db.add(row);db.flush();events.notify(db,u.id,'event.ticket','Ticket confirmed for '+e.title,id)
 db.add(Audit(actor_id=u.id,action='event.ticket_confirmed',target=id,details={'ticket_id':row.id,'cost':row.cost}))
 return serialize(row)

def refund_cancelled(db,e):
 # Called under the event lock. Deterministic ledger keys make repeated cancellation harmless.
 for row in db.scalars(select(EventTicket).where(EventTicket.event_id==e.id,EventTicket.refunded_at==None).order_by(EventTicket.user_id)):
  credit(db,row.user_id,row.cost,'event_ticket_refund',row.id,'event-ticket-refund:'+row.id)
  row.refunded_at=time.time()
  from .events import notify
  notify(db,row.user_id,'event.ticket_refunded',e.title+' cancelled — '+str(row.cost)+' PC refunded',e.id)

def summary(db,e,u):
 row=ticket(db,e.id,u.id) if e.ticket_price else None
 from .payment_policy import actions_enabled
 return {'purchases_enabled':actions_enabled(),'price':e.ticket_price,'entitled':entitled(db,e,u),'receipt':serialize(row) if row else None,'available':max(0,e.capacity-1-sales(db,e.id)) if e.ticket_price else max(0,e.capacity-(db.scalar(select(func.count()).select_from(Attendee).where(Attendee.event_id==e.id,Attendee.state=='active')) or 0))}
