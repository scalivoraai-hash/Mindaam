"""Optional city venue reservations, debited through the existing immutable ledger."""
import time
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import String,Float,Integer,ForeignKey,UniqueConstraint,select
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base,get_db
from .models import uid,User,Ledger,Config,Audit,Event
from .auth import current_user
from .core import Strict,serialize
from .economy import balance,credit,config
from .operations import super_admin
from .expansion import Destination
from . import events
router=APIRouter(prefix='/api')
DURATIONS=[1,3,6,12,24]
# No automatic debits: every reservation quotes and confirms this admin catalogue.
DEFAULTS={'enabled':True,'prices':{'1':100,'3':250,'6':450,'12':800,'24':1400}}

class VenueBooking(Base):
 __tablename__='venue_bookings'
 id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
 request_id:Mapped[str]=mapped_column(String(36))
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),unique=True)
 city:Mapped[str]=mapped_column(String(80),index=True)
 starts_at:Mapped[float]=mapped_column(Float,index=True)
 ends_at:Mapped[float]=mapped_column(Float)
 hours:Mapped[int]=mapped_column(Integer)
 cost:Mapped[int]=mapped_column(Integer)
 ledger_id:Mapped[str]=mapped_column(ForeignKey('wallet_transactions.id'))
 created_at:Mapped[float]=mapped_column(Float,default=time.time)
 __table_args__=(UniqueConstraint('user_id','request_id'),)


def purchased_available(db,user_id):
 # Conservative purchased-first attribution of past spending. XP and earned
 # Credits remain in their existing wallets; this is eligibility, not a new wallet.
 purchased=0
 for row in db.scalars(select(Ledger).where(Ledger.user_id==user_id,Ledger.currency=='credits').order_by(Ledger.created_at,Ledger.id)):
  if row.kind=='purchase' and row.amount>0:purchased+=row.amount
  elif row.amount<0:purchased=max(0,purchased+row.amount)
 return min(purchased,balance(db,user_id))


def settings(db):return config(db,'venue_rental_catalog',DEFAULTS)
def booking(db,event_id):return db.scalar(select(VenueBooking).where(VenueBooking.event_id==event_id))
def destination(db,city):
 d=db.scalar(select(Destination).where(Destination.id==city).with_for_update())
 if not d or d.status!='ACTIVE' or not d.public or not d.joinable:raise HTTPException(409,'Venue unavailable in this destination')
 return d

def conflict(db,city,start,end,event_id):
 return db.scalar(select(VenueBooking.id).where(VenueBooking.city==city,VenueBooking.event_id!=event_id,VenueBooking.starts_at<end,VenueBooking.ends_at>start).limit(1))

@router.get('/venue-rentals/{city}')
def catalogue(city:str,u=Depends(current_user),db=Depends(get_db)):
 destination(db,city)
 return {**settings(db),'city':city,'purchased_credits':purchased_available(db,u.id),
  'reservations':[{'starts_at':b.starts_at,'ends_at':b.ends_at} for b in db.scalars(select(VenueBooking).where(VenueBooking.city==city,VenueBooking.ends_at>time.time(),VenueBooking.starts_at<time.time()+86400*30).order_by(VenueBooking.starts_at).limit(100))]}

class BookingInput(Strict):
 request_id:UUID
 hours:Literal[1,3,6,12,24]
 expected_cost:int=Field(ge=1,le=1000000,strict=True)

@router.post('/events/{id}/venue/booking')
def reserve(id:str,data:BookingInput,u=Depends(current_user),db=Depends(get_db)):
 e=events.get(db,id,u,True)
 if e.host_id!=u.id:raise HTTPException(403,'Only the event creator can purchase a reservation')
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 destination(db,e.city)
 prior=db.scalar(select(VenueBooking).where(VenueBooking.user_id==u.id,VenueBooking.request_id==str(data.request_id)))
 if prior:
  if prior.event_id!=id or prior.hours!=data.hours or prior.cost!=data.expected_cost:raise HTTPException(409,'This confirmation was already used for another reservation')
  return serialize(prior)
 if booking(db,id):raise HTTPException(409,'This event already has a venue reservation')
 if e.venue_experience_type!='auditorium' or e.status not in ['scheduled','draft']:raise HTTPException(409,'Reserve an upcoming auditorium event')
 from .growth import require_access
 require_access(db,u,e.city)
 catalog=settings(db);cost=catalog.get('prices',{}).get(str(data.hours))
 if not catalog.get('enabled') or not isinstance(cost,int) or cost<1:raise HTTPException(409,'Venue reservations are currently unavailable')
 if cost!=data.expected_cost:raise HTTPException(409,'The venue price changed. Review it before confirming.')
 start=e.starts_at;end=start+data.hours*3600
 if start<time.time()-60 or start>time.time()+86400*90:raise HTTPException(422,'Choose a venue start within the next 90 days')
 if conflict(db,e.city,start,end,id):raise HTTPException(409,'This venue is reserved during those times. Choose another start.')
 live=db.scalar(select(Event.id).where(Event.id!=id,Event.city==e.city,Event.venue_experience_type=='auditorium',Event.status=='live',Event.starts_at<end,Event.ends_at>start).limit(1))
 if live:raise HTTPException(409,'An event is using this venue. Choose a later start.')
 if purchased_available(db,u.id)<cost:raise HTTPException(409,'More purchased Credits are needed for this reservation. Open Wallet to buy Credits.')
 row=VenueBooking(id=uid(),request_id=str(data.request_id),user_id=u.id,event_id=id,city=e.city,starts_at=start,ends_at=end,hours=data.hours,cost=cost)
 debit=credit(db,u.id,-cost,'venue_rental',row.id,'venue:'+str(data.request_id));row.ledger_id=debit.id
 db.add(row);e.ends_at=end;db.flush();db.add(Audit(actor_id=u.id,action='venue.reserved',target=row.id,details={'event_id':id,'city':e.city,'hours':data.hours,'cost':cost}))
 return serialize(row)


def start_gate(db,e):
 if e.venue_experience_type!='auditorium':return
 destination(db,e.city)
 row=booking(db,e.id);now=time.time()
 if row:
  if not row.starts_at<=now<row.ends_at:raise HTTPException(409,'Start this event during its reserved venue time')
  e.ends_at=row.ends_at
 elif conflict(db,e.city,now,e.ends_at or now+14400,e.id):raise HTTPException(409,'This venue is reserved for another event during that time')

class VenuePrices(Strict):
 enabled:bool=True
 prices:dict[str,int]

@router.get('/super-admin/venue-rentals')
def admin_read(u=Depends(super_admin),db=Depends(get_db)):
 return {**settings(db),'bookings':[serialize(b) for b in db.scalars(select(VenueBooking).order_by(VenueBooking.created_at.desc()).limit(100))]}

@router.put('/super-admin/venue-rentals')
def admin_save(data:VenuePrices,u=Depends(super_admin),db=Depends(get_db)):
 if set(data.prices)!=set(map(str,DURATIONS)) or any(isinstance(v,bool) or not 1<=v<=1000000 for v in data.prices.values()):raise HTTPException(422,'Set a positive Credit price for each duration')
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 row=db.get(Config,'venue_rental_catalog')
 if not row:row=Config(key='venue_rental_catalog');db.add(row)
 row.value=data.model_dump();db.add(Audit(actor_id=u.id,action='venue.pricing',target='venue_rental_catalog',details=row.value));return row.value
