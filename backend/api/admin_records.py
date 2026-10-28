"""Bounded read models for the existing Super Admin role-gated router."""
import time
from fastapi import HTTPException
from sqlalchemy import select, func, or_
from .models import User, Event, Attendee, Ledger, Report, Audit, Mission, Claim
from .core import serialize


def catalog():
    from .commerce import Payment, Business
    from .operations import AdEnquiry, AdCampaign
    from .venue_rentals import VenueBooking
    from .event_tickets import EventTicket
    from .subscriptions import CustomerSubscription
    from .mobility import RentalLease, RentalAsset
    from .transit import Route, Stop
    from .civic import PublicBuilding
    from .discovery import CityInterest
    return {'events':Event,'payments':Payment,'businesses':Business,'enquiries':AdEnquiry,
        'campaigns':AdCampaign,'reservations':VenueBooking,'tickets':EventTicket,
        'subscriptions':CustomerSubscription,'reports':Report,'audit':Audit,
        'transactions':Ledger,'xp':Ledger,'rentals':RentalLease,'transport':Route,
        'stops':Stop,'buildings':PublicBuilding,'missions':Mission,'claims':Claim,
        'city_requests':CityInterest,'assets':RentalAsset}


def safe_row(row):
    excluded={'password_hash','checkout_url','request_key','customer_id','request_id','idempotency_key',
        'latitude','longitude','x','z','return_position','presentation','lighting','programme','signage'}
    return {k:v for k,v in serialize(row).items() if k not in excluded}


def rows(db, kind, page, limit, q, status, sort, days, event_id='', user_id=''):
    model=catalog().get(kind)
    if model is None: raise HTTPException(404,'Unknown record collection')
    query=select(model)
    if kind in {'transactions','xp'}:query=query.where(Ledger.currency==('xp' if kind=='xp' else 'credits'))
    if q:
        fields=[getattr(model,k) for k in ['id','user_id','host_id','owner_id','actor_id','target','city','destination_id','name','title','username','action','sku','business_name','advertiser'] if hasattr(model,k)]
        query=query.where(or_(*(field.ilike('%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%',escape='\\') for field in fields)))
    status_col=next((getattr(model,k) for k in ['status','state','enabled','currency'] if hasattr(model,k)),None)
    if status and status!='all':
        if status_col is None:raise HTTPException(422,'This collection has no status filter')
        if status_col.key=='enabled':
            if status not in {'true','false'}:raise HTTPException(422,'Use true or false')
            query=query.where(status_col==(status=='true'))
        else:query=query.where(status_col==status)
    if event_id:
        if not hasattr(model,'event_id'):raise HTTPException(422,'No event relation')
        query=query.where(model.event_id==event_id)
    if user_id:
        if not hasattr(model,'user_id'):raise HTTPException(422,'No user relation')
        query=query.where(model.user_id==user_id)
    date_col=next((getattr(model,k) for k in ['created_at','started_at','starts_at'] if hasattr(model,k)),None)
    if days:
        if date_col is None:raise HTTPException(422,'This collection has no creation timestamp')
        query=query.where(date_col>=time.time()-days*86400)
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    primary=list(model.__table__.primary_key.columns)
    name_col=next((getattr(model,k) for k in ['title','name','action','sku','id'] if hasattr(model,k)),primary[0])
    order=name_col.asc() if sort=='name' else (date_col if date_col is not None else primary[0])
    if sort=='newest':order=order.desc()
    objects=list(db.scalars(query.order_by(order,*primary).offset((page-1)*limit).limit(limit)))
    items=[safe_row(row) for row in objects]
    ids={r.get('user_id') or r.get('host_id') or r.get('owner_id') for r in items}-{None}
    names=dict(db.execute(select(User.id,User.username).where(User.id.in_(ids))).all()) if ids else {}
    for r in items:
        uid=r.get('user_id') or r.get('host_id') or r.get('owner_id')
        if uid:r['username']=names.get(uid)
        if 'id' not in r:r['id']=' / '.join(str(r.get(c.key,'')) for c in primary)
    if kind=='reservations' and items:
        events={e.id:e for e in db.scalars(select(Event).where(Event.id.in_([r['event_id'] for r in items])))}
        for r in items:
            e=events.get(r['event_id']);r['event_status']=e.status if e else None;r['event_title']=e.title if e else None
    if kind=='events' and items:
        from .venue_rentals import VenueBooking
        from .event_tickets import EventTicket
        ids=[r['id'] for r in items]
        attendance=dict(db.execute(select(Attendee.event_id,func.count()).where(Attendee.event_id.in_(ids),Attendee.state=='active',Attendee.last_seen>time.time()-90).group_by(Attendee.event_id)).all())
        tickets=dict(db.execute(select(EventTicket.event_id,func.count()).where(EventTicket.event_id.in_(ids),EventTicket.refunded_at==None).group_by(EventTicket.event_id)).all())
        bookings=dict(db.execute(select(VenueBooking.event_id,VenueBooking.id).where(VenueBooking.event_id.in_(ids))).all())
        for r,obj in zip(items,objects):
            r.update(participants=attendance.get(r['id'],0),tickets_sold=tickets.get(r['id'],0),reservation_id=bookings.get(r['id']),
                venue_mode=obj.venue_mode or ('standard' if obj.venue_experience_type!='auditorium' else 'grand_arena' if bookings.get(obj.id) or (obj.programme or {}).get('arena_booking_required') else 'virtual_auditorium'),admission='Paid' if obj.ticket_price else 'Free')
    return {'items':items,'total':total,'page':page,'limit':limit}


def detail(db,kind,id):
    model=catalog().get(kind)
    if model is None or not hasattr(model,'id'):raise HTTPException(404,'Record detail unavailable')
    row=db.get(model,id)
    if row is None:raise HTTPException(404,'Record not found')
    if kind in {'transactions','xp'} and row.currency!=('xp' if kind=='xp' else 'credits'):raise HTTPException(404,'Record not found')
    result={'record':safe_row(row),'kind':kind}
    uid=getattr(row,'user_id',None) or getattr(row,'host_id',None) or getattr(row,'owner_id',None)
    user=db.get(User,uid) if uid else None
    if user:result['user']={'id':user.id,'username':user.username,'display_name':(user.profile or {}).get('display_name','')}
    if kind=='events':
        from .venue_rentals import VenueBooking
        from .venue_modes import mode
        result['record']['venue_mode']=mode(db,row)
        booking=db.scalar(select(VenueBooking).where(VenueBooking.event_id==id))
        result['reservation']=safe_row(booking) if booking else None
    if kind=='payments':
        result['accounting_notice']='GBP checkout record; bank settlement and fees are not recorded. Provider webhook events are not additional sales.'
        result['ledger']=[safe_row(r) for r in db.scalars(select(Ledger).where(Ledger.user_id==row.user_id,Ledger.source==row.id).order_by(Ledger.created_at,Ledger.id).limit(100))]
    if kind=='reservations':
        event=db.get(Event,row.event_id)
        result['record']['event_status']=event.status if event else None
        result['record']['event_title']=event.title if event else None
        result['record']['refunded']=bool(db.scalar(select(Ledger.id).where(Ledger.user_id==row.user_id,Ledger.kind=='venue_refund',Ledger.source==row.id).limit(1)))
    if kind in {'reservations','tickets'}:
        ledger=db.get(Ledger,row.ledger_id)
        result['ledger']=[safe_row(ledger)] if ledger else []
    return result


def directory_rows(db, people):
    from .models import Presence, Session
    from .operations import UserActivity
    ids=[p.id for p in people]
    if not ids:return []
    now=time.time()
    balances={(uid,currency):amount for uid,currency,amount in db.execute(select(Ledger.user_id,Ledger.currency,func.sum(Ledger.amount)).where(Ledger.user_id.in_(ids)).group_by(Ledger.user_id,Ledger.currency))}
    seen=dict(db.execute(select(UserActivity.user_id,func.max(UserActivity.last_seen)).where(UserActivity.user_id.in_(ids)).group_by(UserActivity.user_id)).all())
    presence={p.user_id:p for p in db.scalars(select(Presence).where(Presence.user_id.in_(ids)))}
    sessions=set(db.scalars(select(Session.user_id).where(Session.user_id.in_(ids),Session.expires_at>now)))
    result=[]
    for person in people:
        p=presence.get(person.id);online=bool(p and p.updated_at>now-90 and not person.suspended and person.id in sessions)
        result.append({'id':person.id,'username':person.username,'display_name':(person.profile or {}).get('display_name',''),'email':person.email,'role':person.role,'created_at':person.created_at,'last_seen':max(seen.get(person.id,0),p.updated_at if p else 0) or None,'online':online,'city':p.city if online else person.city,'suspended':person.suspended,'verified':person.verified,'credits':balances.get((person.id,'credits'),0),'xp':balances.get((person.id,'xp'),0)})
    return result
