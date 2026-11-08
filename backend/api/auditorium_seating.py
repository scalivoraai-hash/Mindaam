"""Server-owned occupancy for the existing 36 auditorium chairs."""
import math,time
from sqlalchemy import Integer,String,Float,ForeignKey,select,delete
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
from .models import Presence,Attendee,Event

class Seat(Base):
    __tablename__='auditorium_seats'
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),primary_key=True)
    number:Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),unique=True,index=True)
    occupied_at:Mapped[float]=mapped_column(Float,default=time.time)

# Matches DisplayAssets' existing chair geometry; no new layout or teleport route.
CHAIRS=[(x,-3+row*2.1) for row in range(6) for x in (-7,-5.4,-3.8,3.8,5.4,7)]

def release(db,user_id):
    db.execute(delete(Seat).where(Seat.user_id==user_id))

def synchronize(db,p,u,interior):
    row=db.scalar(select(Seat).where(Seat.user_id==u.id))
    event_id=p.zone_id[6:] if p.zone_id.startswith('event:') else None
    valid=bool(interior and interior.get('template')=='auditorium' and event_id==interior['id'])
    if row and (not valid or row.event_id!=event_id or p.motion_speed>0):
        release(db,u.id);row=None
    if not valid:return None
    if row:
        if math.dist((p.x,p.z),CHAIRS[row.number])>.9:
            release(db,u.id);return None
        return row.number
    if p.motion_speed>0 or time.time()-p.last_move<.8:return None
    choices=sorted((math.dist((p.x,p.z),point),i) for i,point in enumerate(CHAIRS))
    if choices[0][0]>.85:return None
    # Vacate absent or departed attendees. Current player's User/Presence locks
    # protect their transition. Unique chair and user keys arbitrate other users.
    active=select(Attendee.user_id).join(Presence,Presence.user_id==Attendee.user_id).where(
        Attendee.event_id==event_id,Attendee.state=='active',
        Presence.zone_id=='event:'+event_id,Presence.updated_at>time.time()-45)
    db.execute(delete(Seat).where(Seat.event_id==event_id,~Seat.user_id.in_(active)))
    if db.bind.dialect.name=='postgresql':from sqlalchemy.dialects.postgresql import insert
    else:from sqlalchemy.dialects.sqlite import insert
    for distance,number in choices:
        if distance>.85:break
        claimed=db.execute(insert(Seat).values(event_id=event_id,number=number,user_id=u.id,occupied_at=time.time()).on_conflict_do_nothing().returning(Seat.number)).scalar_one_or_none()
        if claimed is not None:
            p.x,p.z=CHAIRS[number];p.motion_speed=0;p.last_move=time.time()
            return number
    return None

def occupancy(db,event_id):
    return dict(db.execute(select(Seat.user_id,Seat.number).where(Seat.event_id==event_id)).all())
