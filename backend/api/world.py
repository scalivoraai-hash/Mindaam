from .auth import display_profile
import os
import logging
import math
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select, func, or_, and_
from .db import get_db, APP_ENV
from .geography import district, walkable, traversable, safe_step, nearest_safe_position, safe_spawn
from .models import *
from .auth import current_user
from .economy import credit, config, balance
from .core import Strict, check_city, CITIES, emit, serialize

router = APIRouter(prefix="/api")


class CityInput(Strict):
    city: str


class Movement(Strict):
    dx: float = Field(ge=-1, le=1, allow_inf_nan=False)
    dz: float = Field(ge=-1, le=1, allow_inf_nan=False)
    mode: str = "walk"
    city: str | None = Field(default=None,max_length=50)
    zone: str | None = Field(default=None,max_length=100)


# The unchanged preview input is the pace reference. One shared, packaged contract.
import json
from pathlib import Path
MOVEMENT = json.loads((Path(__file__).resolve().parents[2]/'shared/movement.json').read_text())
WALK_SPEED = MOVEMENT['previewStep'] / (MOVEMENT['inputIntervalMs'] / 1000)
RUN_SPEED = WALK_SPEED * MOVEMENT['runMultiplier']
OUTDOOR_WALK_SPEED = WALK_SPEED * MOVEMENT['normalWorldMultiplier'] * MOVEMENT['outdoorWalkFactor']
OUTDOOR_RUN_SPEED = RUN_SPEED * MOVEMENT['normalWorldMultiplier']
WALK_ACCELERATION = WALK_SPEED / MOVEMENT['accelerationSeconds']
RUN_ACCELERATION = RUN_SPEED / MOVEMENT['accelerationSeconds']


def blocked(db, a, b):
    return (
        db.scalar(
            select(Social.id).where(
                Social.kind == "block",
                or_(
                    and_(Social.actor == a, Social.target == b),
                    and_(Social.actor == b, Social.target == a),
                ),
            )
        )
        is not None
    )


def friends(db, a, b):
    return (
        db.scalar(
            select(Social.id).where(
                Social.kind == "friend", Social.actor == a, Social.target == b
            )
        )
        is not None
    )


def visible(db, viewer, target, p, pviewer):
    if (
        p.zone_id != pviewer.zone_id
        or blocked(db, viewer.id, target.id)
        or target.privacy == "Ghost Mode"
        or target.suspended
    ):
        return False
    if target.privacy == "Friends Only" and not friends(db, viewer.id, target.id):
        return False
    if target.privacy == "Event Mode" and not p.zone_id.startswith('event:'):
        return False  # fail closed until shared-event presence exists
    if (
        target.privacy == "Zone Mode"
        and math.hypot(p.x - pviewer.x, p.z - pviewer.z) > 60
    ):
        return False
    return math.hypot(p.x - pviewer.x, p.z - pviewer.z) <= 180


def snapshot(db, u, city):
    db.scalar(select(User.id).where(User.id==u.id).with_for_update())
    check_city(city)
    from .growth import require_access
    require_access(db,u,city)
    own = db.get(Presence, u.id)
    if not own or own.city != city:
        raise HTTPException(409, "Enter this city first")
    own.updated_at = time.time()
    from . import transit,civic,operations
    ride=transit.journey(db,u)
    if ride and own.zone_id.startswith('bus:'):
        seat_position=transit.passenger_position(ride,ride['seat']);own.x=seat_position['x'];own.z=seat_position['z'];own.mode='bus'
    from . import mobility
    rental=mobility.snapshot(db,u)
    interior=civic.scene(db,own)
    from .events import auditorium_scene
    interior=interior or auditorium_scene(db,own,u)
    operations.activity(db,u)
    claimed = select(Claim.collectible_id).where(Claim.user_id == u.id)
    objects = db.scalars(
        select(Collectible).where(
            Collectible.city == city,
            Collectible.active == True,
            Collectible.starts_at <= time.time(),
            Collectible.ends_at > time.time(),
            Collectible.claims < Collectible.max_claims,
            ~Collectible.id.in_(claimed),
        )
    ).all()
    from .collectible_rotation import visible as rotating_items
    objects=rotating_items(db,u,city,objects) if own.zone_id=='world' else objects
    players = []
    from .player_presentation import transport_states,presentation
    sampled_at=time.time()
    rentals,passengers=transport_states(db,city,sampled_at)
    for p, target in db.execute(
        select(Presence, User)
        .join(User, User.id == Presence.user_id)
        .where(
            or_(Presence.city == city, Presence.user_id.in_(list(passengers))),
            Presence.updated_at > time.time() - 45,
            Presence.user_id != u.id,
            User.id.in_(select(Session.user_id).where(Session.expires_at>time.time())),
        )
    ):
        projected,render_state=presentation(p,rentals,passengers,sampled_at)
        # Exterior passenger projection is visual only. Social/proximity authorization
        # still uses the real bus zone; interiors and privacy remain isolated.
        if own.zone_id=='world' and render_state['vehicle'] and render_state['vehicle']['kind']=='bus':
            projected.zone_id='world'
        if ride and p.zone_id==own.zone_id:
            ticket=db.scalar(select(transit.Ticket).where(transit.Ticket.user_id==target.id,transit.Ticket.state=='aboard'))
            if ticket:
                seat_position=transit.passenger_position(ride,ticket.seat)
                projected.x,projected.z=seat_position['x'],seat_position['z']
                render_state.update(**seat_position,seated=ticket.seat is not None)
                render_state['vehicle']={'id':ride['vehicle_id'],'kind':'bus','seat':ticket.seat,**ride['position'],'sampled_at':sampled_at}
                render_state['movement_state']='ON_BUS'
        if projected.city==city and visible(db, u, target, projected, own):
            players.append(
                {
                    "id": target.id,
                    "username": target.username,
                    "avatar": target.avatar,
                **display_profile(target),
                    **render_state,
                    "mode": p.mode,
                    "online": True,
                    "distance": round(math.hypot(projected.x-own.x,projected.z-own.z)),
                    "interests": target.interests,
                }
            )
    if interior and interior.get('template')=='auditorium':
        roles={a.user_id:a.role for a in db.scalars(select(Attendee).where(Attendee.event_id==interior['id'],Attendee.state=='active'))}
        players=[p for p in players if p['id'] in roles]
        players.sort(key=lambda p:(roles[p['id']] not in ['host','cohost','speaker'],p['distance'],p['id']))
        players=players[:48]
        for p in players:p['event_role']=roles[p['id']];p['y']=.7 if p['z']<-6 else 0
    from .commerce import world_businesses
    from .business_spatial import BusinessSpatial
    from .talk import rules
    district_online=1
    for presence,target in db.execute(select(Presence,User).join(User,User.id==Presence.user_id).where(Presence.city==city,Presence.updated_at>time.time()-45,User.id!=u.id,User.suspended==False)):
        if not blocked(db,u.id,target.id) and (target.privacy=='City Mode' or (target.privacy=='Friends Only' and friends(db,u.id,target.id))):district_online+=1
    from .events import visible as event_visible
    markers=[{'id':e.id,'title':e.title,'x':e.x,'z':e.z,'mode':e.communication_mode,'participants':db.scalar(select(func.count()).select_from(Attendee).where(Attendee.event_id==e.id,Attendee.state=='active'))} for e in db.scalars(select(Event).where(Event.city==city,Event.status=='live',Event.x!=None,Event.z!=None).limit(20)) if event_visible(db,e,u)]
    from .movement_policy import public as movement_config
    return {
        "movement_config":movement_config(db),
        "server_time":sampled_at,
        "events":markers,
        "scene":interior,
        "journey":ride,
        "rental":rental,
        "rental_assets":mobility.nearby(db,own),
        "public_buildings":civic.listing(db,city,own.x,own.z) if own.zone_id=='world' else [],
        "ad_boards":operations.boards(db,city) if own.zone_id=='world' else [],
        "transit":transit.board(city,u,db) if own.zone_id=='world' else None,
        "city": city,
        "zone": next(c["zone"] for c in CITIES if c["id"] == city),
        "position": {"x": own.x, "z": own.z, "mode": own.mode, "last_move": own.last_move,"zone_id":own.zone_id,"y":transit.passenger_position(ride,ride['seat'])['y'] if ride else .7 if interior and interior.get('template')=='auditorium' and own.z<-6 else 0},
        "collectibles": [] if own.zone_id!='world' else [
            serialize(c) for c in objects if math.hypot(c.x - own.x, c.z - own.z) < 200
        ],
        "players": players,
        "indoor_business_sources":[s.split(':osm:')[-1] for s in db.scalars(select(BusinessSpatial.source_id).where(BusinessSpatial.parent_building_id!=None,BusinessSpatial.source_id.like(city+':osm:%')))] if own.zone_id=='world' else [],
        "businesses": world_businesses(db, city, own.x, own.z) if own.zone_id=='world' else [],
        "social_rules": rules(),
        "online": district_online,
        "nearby_online": len(players)+1,
        "simulated": True,
    }


@router.post("/world/enter")
def enter(data: CityInput, u=Depends(current_user), db=Depends(get_db)):
    db.scalar(select(User.id).where(User.id==u.id).with_for_update())
    check_city(data.city)
    if not u.onboarded:
        raise HTTPException(409, "Complete onboarding")
    from .growth import require_access,event
    require_access(db,u,data.city)
    event(db,u,"world_entered_after_unlock",data.city);event(db,u,"world_entered",data.city)
    from .civic import restore_visit
    restore_visit(db,u,data.city)
    p = db.get(Presence, u.id)
    from .transit import current
    ride=current(db,u)
    from . import mobility
    lease=mobility.current(db,u)
    if lease:
        asset=db.get(mobility.RentalAsset,lease.asset_id)
        if data.city!=asset.city:raise HTTPException(409,'Exit your rental before changing worlds')
        if not p:
            mobility.finish(db,u,lease);p=db.get(Presence,u.id)
    if ride:
        from .transit import Vehicle,Route
        route=db.get(Route,db.get(Vehicle,ride.vehicle_id).route_id)
        if data.city!=route.origin:raise HTTPException(409,'Get off the bus before changing worlds')
        if p:p.zone_id='bus:'+ride.vehicle_id;p.mode='bus'
    if p and p.zone_id!='world' and p.city!=data.city:raise HTTPException(409,'Exit your vehicle or building before changing worlds')
    if not p:
        spawn = safe_spawn(data.city) if APP_ENV != "test" else [0, 0]
        db.add(Presence(user_id=u.id, city=data.city, x=spawn[0], z=spawn[1],zone_id='bus:'+ride.vehicle_id if ride else 'world',mode='bus' if ride else 'walk'))
    elif p.city != data.city:
        p.city = data.city
        spawn = safe_spawn(data.city) if APP_ENV != "test" else [0, 0]
        p.x, p.z = spawn
        p.mode = "walk"
        p.last_move = time.time()
    if p and not lease and p.zone_id=='world' and APP_ENV != "test" and not traversable(data.city,p.x,p.z):
        p.x,p.z=nearest_safe_position(data.city,p.x,p.z,recovery_radius()) or safe_spawn(data.city)
    from .discovery import record_stamp

    record_stamp(db, u.id, data.city)
    u.city = data.city
    db.flush()
    emit(db, u, "city_entered", data.city)
    return snapshot(db, u, data.city)


@router.get("/world/{city}")
def world(city: str, u=Depends(current_user), db=Depends(get_db)):
    return snapshot(db, u, city)


@router.post("/world/move")
def move(data: Movement, u=Depends(current_user), db=Depends(get_db)):
    db.scalar(select(User.id).where(User.id==u.id).with_for_update())
    p = db.scalar(select(Presence).where(Presence.user_id == u.id).with_for_update())
    if not p:
        raise HTTPException(409, "Enter world first")
    if (data.city is not None and data.city!=p.city) or (data.zone is not None and data.zone!=p.zone_id):
        raise HTTPException(409,'Your location changed. Movement was cleared.')
    from .mobility import current as rental_current
    if rental_current(db,u):raise HTTPException(409,'Use your vehicle controls or Exit Vehicle')
    if p.zone_id.startswith('bus:'):raise HTTPException(409,'Choose a seat or wait for the bus to stop')
    from .movement_policy import public as movement_config
    policy=movement_config(db)
    speeds = policy["speeds"] if p.zone_id == "world" else {"walk":WALK_SPEED,"run":RUN_SPEED}
    if data.mode not in speeds:
        raise HTTPException(422, "Unsupported movement mode")
    if data.mode not in {"walk", "run"}:
        raise HTTPException(403,'Pick up a configured rental first; existing vehicle access is honoured there')
    now = time.time()
    dt = min(max(now - p.last_move, 0), 0.3)
    if now-p.last_move>.5:dt=MOVEMENT['inputIntervalMs']/1000
    length = max(1, math.hypot(data.dx, data.dz))
    # Preview-matched walking and a distinct faster run use the same shared contract.
    # Released input stops immediately. Render interpolation supplies the soft stop.
    previous = p.motion_speed if now-p.last_move < .5 else 0
    acceleration=speeds[data.mode]/MOVEMENT['accelerationSeconds']
    speed = min(speeds[data.mode], previous+acceleration*dt)
    if not (data.dx or data.dz):speed=0
    old_x,old_z=p.x,p.z
    x = p.x + data.dx / length * speed * dt
    z = p.z + data.dz / length * speed * dt
    recovered=False
    if p.zone_id.startswith(('building:','event:')):
        if data.mode not in ['walk','run']:raise HTTPException(409,'Walk inside the venue')
        if p.zone_id.startswith('event:'):
            attendee=db.get(Attendee,(p.zone_id[6:],u.id))
            if not attendee or attendee.state!='active':raise HTTPException(409,'You are no longer in this event')
            if attendee.role=='audience':z=max(-5,z)
        if abs(x)<2 and z>=13.4 and data.dz>0:
            if p.zone_id.startswith('building:'):
                from .civic import exit_building
                exit_building(db,u)
            else:
                from .events import exit_venue
                exit_venue(p.zone_id[6:],u,db)
            return {'x':p.x,'z':p.z,'mode':p.mode,'zone_id':p.zone_id,'last_move':p.last_move,'exited':True}
        back=-14
        if p.zone_id.startswith('building:'):
            from .business_spatial import BusinessSpatial
            count=db.scalar(select(func.count()).select_from(BusinessSpatial).where(BusinessSpatial.parent_building_id==p.zone_id[9:]))
            back=min(-14,7-((count+1)//2)*4) if count else -14
        p.x,p.z=max(-10,min(10,x)),max(back,min(14,z))
    elif APP_ENV == 'test':
        if abs(x)<=14 or abs(z)<=14:
            p.x,p.z=max(-180,min(180,x)),max(-180,min(180,z))
    else:
        if not traversable(p.city,p.x,p.z):
            safe=nearest_safe_position(p.city,p.x,p.z,recovery_radius())
            if safe:
                p.x,p.z=safe;recovered=True
                db.add(Audit(actor_id=u.id,action='world.stuck_recovered',target=p.city))
                logging.getLogger('pulseworld').info('Recovered invalid virtual position')
        if traversable(p.city,p.x,p.z):
            p.x,p.z=safe_step(p.city,p.x,p.z,data.dx/length*speed*dt,data.dz/length*speed*dt,data.mode)
    p.mode = data.mode
    p.last_move = now
    p.updated_at = now
    p.motion_speed = speed
    from .motion_diagnostics import observe
    observe(u.id,p.city,p.zone_id,p.mode,p.x,p.z,bool(speed),bool(speed and dt>.03 and math.hypot(p.x-old_x,p.z-old_z)<.01))
    return {"x": p.x, "z": p.z, "mode": p.mode, "zone_id":p.zone_id,
            "speed":math.hypot(p.x-old_x,p.z-old_z)/dt if dt else 0,
            "blocked":bool(speed and dt>.03 and math.hypot(p.x-old_x,p.z-old_z)<.01),
            "recovered": recovered, "last_move": p.last_move, "movement_config":policy}


def recovery_radius():
    return max(.25,min(3,float(os.getenv('WORLD_RECOVERY_METRES','3'))))

class RecoveryInput(Strict):
    device: str = Field(default='unknown',pattern='^(touch|pointer|unknown)$')
    performance: str = Field(default='unknown',pattern='^(low|normal|unknown)$')

@router.post('/world/unstuck')
def unstuck(data:RecoveryInput|None=None,u=Depends(current_user),db=Depends(get_db)):
    db.scalar(select(User.id).where(User.id==u.id).with_for_update())
    p=db.scalar(select(Presence).where(Presence.user_id==u.id).with_for_update())
    if not p:raise HTTPException(409,'Enter world first')
    if p.zone_id!='world':raise HTTPException(409,'Use the venue or vehicle exit')
    from .mobility import current as rental_current
    if rental_current(db,u):raise HTTPException(409,'Use Exit Vehicle to recover safely')
    last=db.scalar(select(Audit).where(Audit.actor_id==u.id,Audit.action=='world.unstuck').order_by(Audit.created_at.desc()).limit(1))
    if last and last.created_at>time.time()-30:raise HTTPException(429,'Wait 30 seconds before trying recovery again')
    safe=nearest_safe_position(p.city,p.x,p.z,recovery_radius())
    if not safe:raise HTTPException(409,'No nearby safe position found. Try moving back along your path.')
    changed=math.hypot(safe[0]-p.x,safe[1]-p.z)>.01
    p.x,p.z=safe;p.mode='walk';p.last_move=time.time();p.updated_at=time.time()
    db.add(Audit(actor_id=u.id,action='world.unstuck',target=p.city,details={'recovered':changed,'zone':p.zone_id,'collider':'invalid_ground' if changed else 'path_edge_or_obstacle',**(data or RecoveryInput()).model_dump()}))
    return {'x':p.x,'z':p.z,'mode':p.mode,'recovered':changed,'last_move':p.last_move,'message':'Moved to the nearest safe position.' if changed else 'You are on safe ground. Turn away from the obstacle to continue.'}


def mission_views(db, u):
    counts = dict(
        db.execute(
            select(Collectible.kind, func.count(Claim.id))
            .join(Claim, Claim.collectible_id == Collectible.id)
            .where(Claim.user_id == u.id, Collectible.city == u.city)
            .group_by(Collectible.kind)
        ).all()
    )
    done = set(
        db.scalars(
            select(MissionCompletion.mission_id).where(
                MissionCompletion.user_id == u.id
            )
        )
    )
    return [
        {
            **serialize(m),
            "credits": 0,
            "progress": {
                k: min(counts.get(k, 0), v) for k, v in m.requirements.items()
            },
            "completed": m.id in done,
            "eligible": all(counts.get(k, 0) >= v for k, v in m.requirements.items()),
        }
        for m in db.scalars(select(Mission).where(Mission.city == u.city))
    ]


@router.get("/missions")
def missions(u=Depends(current_user), db=Depends(get_db)):
    return mission_views(db, u)


@router.post("/collectibles/{object_id}/claim")
def collect(object_id: str, u=Depends(current_user), db=Depends(get_db)):
    db.scalar(select(User).where(User.id == u.id).with_for_update())
    c = db.scalar(
        select(Collectible).where(Collectible.id == object_id).with_for_update()
    )
    p = db.get(Presence, u.id)
    if p and p.zone_id!='world':raise HTTPException(409,'Return to the world to collect')
    if not c:
        from .collectible_rotation import materialize
        c=materialize(db,object_id,p)
    if not c:
        raise HTTPException(404, "Collectible not found")
    existing = db.scalar(
        select(Claim).where(Claim.user_id == u.id, Claim.collectible_id == object_id)
    )
    if existing:
        return {
            "claimed": True,
            "already_claimed": True,
            "awarded_xp": 0,
            "awarded_credits": 0,
            "credits": balance(db, u.id),
            "xp": balance(db, u.id, "xp"),
            "missions": mission_views(db, u),
        }
    now = time.time()
    if not c.active or not c.starts_at <= now < c.ends_at or c.claims >= c.max_claims:
        raise HTTPException(409, "This collectible is no longer available")
    if (
        not p
        or p.city != c.city
        or p.updated_at < now - 45
        or math.hypot(p.x - c.x, p.z - c.z) > 5
    ):
        raise HTTPException(409, "Move closer to collect this item")
    from .collectible_rotation import guard
    guard(db,u,c)
    before_xp = balance(db, u.id, "xp")
    before_credits = balance(db, u.id)
    db.add(Claim(user_id=u.id, collectible_id=c.id))
    c.claims += 1
    credit(
        db,
        u.id,
        5 if c.kind == "fruit" else 15,
        "collectible",
        c.id,
        "collect:" + c.id,
        currency="xp",
    )
    db.flush()
    emit(db, u, c.kind + "_collected", c.id)
    for m in mission_views(db, u):
        if m["eligible"] and not m["completed"]:
            db.add(MissionCompletion(user_id=u.id, mission_id=m["id"]))
            credit(
                db,
                u.id,
                m["xp"],
                "mission",
                m["id"],
                "mission:" + m["id"],
                currency="xp",
            )
            db.flush()
            emit(db, u, "mission_completed", m["id"])
            r = db.get(Referral, u.id)
            if r and not r.rewarded and u.verified:
                parent = db.get(User, r.referrer_id)
                if parent and not parent.suspended:
                    r.rewarded = True
    return {
        "claimed": True,
        "awarded_xp": balance(db, u.id, "xp") - before_xp,
        "awarded_credits": balance(db, u.id) - before_credits,
        "credits": balance(db, u.id),
        "xp": balance(db, u.id, "xp"),
        "missions": mission_views(db, u),
    }


class Rental(Strict):
    mode: str


@router.post("/transport/rent")
def rent(data: Rental, u=Depends(current_user), db=Depends(get_db)):
    raise HTTPException(409,{'code':'RENTAL_PICKUP_REQUIRED','message':'Open Rentals and pick up a vehicle. Existing paid access remains valid.'})


@router.get("/leaderboard")
def leaderboard(u=Depends(current_user), db=Depends(get_db)):
    rows = db.execute(
        select(User, func.sum(Ledger.amount).label("xp"))
        .join(Ledger, Ledger.user_id == User.id)
        .where(
            Ledger.currency == "xp",
            User.suspended == False,
            User.privacy != "Ghost Mode",
        )
        .group_by(User.id)
        .order_by(func.sum(Ledger.amount).desc())
        .limit(50)
    ).all()
    return [
        {
            "id": p.id,
            "username": p.username,
            "city": p.city,
            "xp": xp,
            "avatar": p.avatar,
        }
        for p, xp in rows
        if not blocked(db, u.id, p.id)
    ]
