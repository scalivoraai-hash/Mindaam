"""Read-only control-centre aggregates. Virtual units never become cash revenue."""
import time
from datetime import datetime, timezone
from sqlalchemy import select, func, case, and_, or_, union_all, literal
from .models import User, Ledger, Event, Attendee, MediaSession, Social, Report, Presence, Session


def day_series(db, column, measures, start, end):
    # Reuse one expression/bind identity: PostgreSQL rejects independently bound
    # SELECT/GROUP BY expressions even when the Python constants are equal.
    bucket = func.floor(column / 86400).label('day')
    return [dict(row._mapping) for row in db.execute(
        select(bucket, *measures).where(column >= start, column < end)
        .group_by(bucket).order_by(bucket))]


def enrich(db, result, start, end, now):
    from .operations import UserActivity, AdEnquiry, AdCampaign
    from .commerce import Payment
    from .event_tickets import EventTicket
    from .venue_rentals import VenueBooking
    from .growth import GrowthEvent, WorldAccess, ShareAction
    count = lambda model, *where: db.scalar(select(func.count()).select_from(model).where(*where)) or 0
    window = lambda column: (column >= start, column < end)
    total = lambda column, *where: db.scalar(select(func.coalesce(func.sum(column), 0)).where(*where)) or 0
    k = result['kpis']
    k['total_events'] = count(Event)
    venue=case((Event.venue_mode!=None,Event.venue_mode),(Event.venue_experience_type!='auditorium','standard'),
        (or_(Event.programme['arena_booking_required'].as_boolean()==True,select(VenueBooking.id).where(VenueBooking.event_id==Event.id).exists()),'grand_arena'),else_='virtual_auditorium')
    venue_counts=dict(db.execute(select(venue.label('venue'),func.count()).group_by(venue)).all())
    for mode in ('standard','virtual_auditorium','grand_arena'):k[mode+'_events']=venue_counts.get(mode,0)
    result['event_activity']=[{'type':mode,'count':n} for mode,n in db.execute(select(venue.label('venue'),func.count()).where(*window(Event.created_at)).group_by(venue))]

    k['scheduled_events'] = count(Event, Event.status == 'scheduled')
    k['completed_events'] = count(Event, Event.status == 'ended')
    k['cancelled_events'] = count(Event, Event.status == 'cancelled')
    k['free_events'] = count(Event, Event.ticket_price == 0)
    k['ticketed_events'] = count(Event, Event.ticket_price > 0)
    k['tickets_sold'] = count(EventTicket, EventTicket.refunded_at == None, *window(EventTicket.created_at))
    k['active_event_participants'] = count(Attendee, Attendee.state == 'active', Attendee.last_seen > now - 90,
        Attendee.event_id.in_(select(Event.id).where(Event.status == 'live')))
    k['arena_reservations'] = count(VenueBooking, *window(VenueBooking.created_at))
    k['active_voice_sessions'] = count(MediaSession, MediaSession.state == 'accepted', MediaSession.kind == 'voice', MediaSession.ended_at == None)
    k['active_conversations'] = count(MediaSession, MediaSession.state == 'accepted', MediaSession.conversation_id != None, MediaSession.ended_at == None)
    k['active_liveface'] = count(MediaSession, MediaSession.state == 'accepted', MediaSession.kind == 'liveface', MediaSession.ended_at == None)
    # Friend acceptance writes reciprocal edges; count each unordered pair once.
    k['friend_connections'] = count(Social, Social.kind == 'friend', Social.actor < Social.target)
    k['follow_relationships'] = count(Social, Social.kind == 'follow')
    k['moderation_reports'] = count(Report)
    k['pending_reports'] = count(Report, Report.status == 'open')
    k['returning_users'] = db.scalar(select(func.count(func.distinct(UserActivity.user_id))).join(User, User.id == UserActivity.user_id).where(User.created_at < start, UserActivity.last_seen >= start, UserActivity.last_seen < end)) or 0
    k['outstanding_credit_balances'] = total(Ledger.amount, Ledger.currency == 'credits')
    k['credits_earned'] = total(Ledger.amount, Ledger.currency == 'credits', Ledger.amount > 0, Ledger.kind.in_(['collectible','mission','daily','referral','visit','welcome']), *window(Ledger.created_at))
    k['xp_awarded'] = total(Ledger.amount, Ledger.currency == 'xp', Ledger.amount > 0, *window(Ledger.created_at))
    for key, kinds in {'event_ticket_spending':['event_ticket'], 'grand_arena_spending':['venue_rental'], 'rental_spending':['vehicle_rental'], 'credit_refunds':['venue_refund','event_ticket_refund','purchase_refund']}.items():
        k[key] = total(Ledger.amount, Ledger.currency == 'credits', Ledger.kind.in_(kinds), *window(Ledger.created_at))
        if key.endswith('spending'): k[key] = -k[key]
    k['rental_xp_spent'] = -total(Ledger.amount, Ledger.currency=='xp', Ledger.amount<0, Ledger.kind.in_(['car_rental_xp','bike_rental_xp']), *window(Ledger.created_at))
    k['transport_xp_spent'] = -total(Ledger.amount, Ledger.currency=='xp', Ledger.amount<0, Ledger.kind=='bus_ticket_xp', *window(Ledger.created_at))
    k['credit_adjustments'] = total(Ledger.amount, Ledger.currency == 'credits', Ledger.kind.like('admin_%'), *window(Ledger.created_at))
    confirmed = Payment.status.in_(['paid','refunded','partially_refunded'])
    # A Payment is the unique checkout record; never join webhook deliveries.
    k['gross_payments_pence'] = total(Payment.amount_pence, confirmed, *window(Payment.created_at))
    k['total_gross_payments_pence'] = total(Payment.amount_pence, confirmed)
    month = datetime.fromtimestamp(now, timezone.utc).replace(day=1,hour=0,minute=0,second=0,microsecond=0).timestamp()
    k['month_gross_payments_pence'] = total(Payment.amount_pence, confirmed, Payment.created_at >= month)
    k['refund_pence'] = total(Payment.refunded_pence, confirmed, *window(Payment.created_at))
    k['completed_purchases'] = count(Payment, confirmed, *window(Payment.created_at))
    k['failed_payments'] = count(Payment, Payment.status.in_(['failed','expired','cancelled']), *window(Payment.created_at))
    result['payment_trend'] = day_series(db, Payment.created_at, [func.sum(case((confirmed, Payment.amount_pence),else_=0)).label('gross_pence'),func.count().label('checkouts')], start,end)
    result['payment_products'] = [dict(r._mapping) for r in db.execute(select(Payment.sku.label('product'),func.count().label('count'),func.sum(Payment.amount_pence).label('gross_pence')).where(confirmed,*window(Payment.created_at)).group_by(Payment.sku))]
    result['payment_status'] = [{'status':s,'count':n} for s,n in db.execute(select(Payment.status,func.count()).where(*window(Payment.created_at)).group_by(Payment.status))]
    result['event_status'] = [{'status':s,'count':n} for s,n in db.execute(select(Event.status,func.count()).group_by(Event.status))]
    result['event_trend'] = day_series(db,Event.created_at,[func.count().label('count')],start,end)
    result['world_trend'] = day_series(db,GrowthEvent.created_at,[func.sum(case((GrowthEvent.kind=='world_entered',1),else_=0)).label('visits')],start,end)
    visits = dict(db.execute(select(GrowthEvent.destination_id,func.count()).where(GrowthEvent.kind=='world_entered',*window(GrowthEvent.created_at)).group_by(GrowthEvent.destination_id)).all())
    events = dict(db.execute(select(Event.city,func.count()).group_by(Event.city)).all())
    for row in result['worlds']:
        row.update(visits=visits.get(row['id'],0),events=events.get(row['id'],0),active_sessions=row['online'])
    result['worlds'].sort(key=lambda r:(-r['online'],-r['visits'],r['id']))
    k['city_visits'] = sum(visits.values())
    k['unlocked_world_accesses'] = count(WorldAccess)
    live = select(Presence.city,Presence.zone_id).join(User,User.id==Presence.user_id).where(Presence.updated_at>now-45,User.suspended==False,Presence.user_id.in_(select(Session.user_id).where(Session.expires_at>now))).distinct().subquery()
    k['active_districts'] = db.scalar(select(func.count()).select_from(live)) or 0
    # Historical rolling users calculated from recorded activity days, not samples.
    first_day,last_day=int(start/86400),int((end-0.001)/86400)
    days=union_all(*(select(literal(d).label('day')) for d in range(first_day,last_day+1))).subquery()
    result['active_trend']=[dict(row._mapping) for row in db.execute(
        select(days.c.day,
            func.count(func.distinct(case((UserActivity.day==days.c.day,UserActivity.user_id)))).label('daily'),
            func.count(func.distinct(case((UserActivity.day>=days.c.day-6,UserActivity.user_id)))).label('weekly'),
            func.count(func.distinct(UserActivity.user_id)).label('monthly'))
        .join(UserActivity,and_(UserActivity.day>=days.c.day-29,UserActivity.day<=days.c.day))
        .group_by(days.c.day).order_by(days.c.day))]
    result['growth']={'shares_by_channel':dict(db.execute(select(ShareAction.channel,func.count()).where(*window(ShareAction.created_at)).group_by(ShareAction.channel)).all()),'unlocks':count(WorldAccess,WorldAccess.source=='share',*window(WorldAccess.created_at)), 'registration_conversions':count(GrowthEvent,GrowthEvent.kind=='invite_registration',*window(GrowthEvent.created_at))}
    result['range']={'start':start,'end':end,'timezone':'UTC'}
    result['unavailable_metrics']=['Bank settlement, fees and subscription cash revenue are not recorded.', 'Arena utilisation cannot be inferred without a recorded available-capacity calendar.', 'World visits include only consented recorded activity; no GPS is exposed.']
    result['history_notice']='UTC reporting. Activity charts show recorded observations only. Live counts are current; event totals and wallet balances are lifetime; flows use the selected period. Payment dates are checkout cohorts, not settlement dates.'
    return result


def online_series(db,start,end):
    from .operations import OnlineSample
    samples=select(OnlineSample.bucket,func.sum(OnlineSample.count).label('online')).where(OnlineSample.bucket>=int(start/300),OnlineSample.bucket<int(end/300)).group_by(OnlineSample.bucket).subquery()
    seconds=3600 if end-start<=2*86400 else 86400
    bucket=func.floor(samples.c.bucket*300/seconds).label('period')
    return [{'time':int(period)*seconds,'count':n} for period,n in db.execute(select(bucket,func.max(samples.c.online)).group_by(bucket).order_by(bucket))]
