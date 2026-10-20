"""Truthful city discovery, opt-in demand and earned virtual passport stamps."""

import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, Float, ForeignKey, select, func
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, get_db
from .models import User, Audit, Presence, Session, Event
from .auth import current_user
from .core import CITIES

router = APIRouter(prefix="/api")


class CityInterest(Base):
    __tablename__ = "city_interests"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    city: Mapped[str] = mapped_column(String(50), primary_key=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    source: Mapped[str] = mapped_column(String(60), default="legacy")
    invite_code: Mapped[str] = mapped_column(String(40), default="")


class PassportStamp(Base):
    __tablename__ = "passport_stamps"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    city: Mapped[str] = mapped_column(String(50), primary_key=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


PLANNED = ("manchester", "liverpool", "leeds", "bristol", "edinburgh", "glasgow")


def catalog(db=None):
    from .expansion import Destination, destination_view, default_threshold, flag
    if db is None:
        return [{**c,'enabled':True,'public':True,'joinable':True,'status':'ACTIVE','country':c.get('country','GB'),'flag':flag(c.get('country','GB'))} for c in CITIES]
    # Read shared configuration once per catalog, without caching admin changes
    # across requests. Realtime transit boards also use this catalog.
    threshold = default_threshold(db)
    return sorted([destination_view(db,d,threshold=threshold) for d in db.scalars(select(Destination))],key=lambda c:(c['priority'],c['name']))


def record_stamp(db, user_id, city):
    """Only call after a server-validated city entry, inside its transaction."""
    if city not in {c["id"] for c in CITIES}:
        raise HTTPException(422, "City not enabled")
    db.scalar(select(User.id).where(User.id == user_id).with_for_update())
    if not db.get(PassportStamp, (user_id, city)):
        db.add(PassportStamp(user_id=user_id, city=city))
        db.flush()


def cities(db=Depends(get_db),include_disabled:bool=False):
    counts = dict(
        db.execute(
            select(CityInterest.city, func.count()).group_by(CityInterest.city)
        ).all()
    )
    alive=select(Session.user_id).where(Session.expires_at>time.time())
    online=dict(db.execute(select(Presence.city,func.count()).join(User,User.id==Presence.user_id).where(Presence.updated_at>time.time()-45,User.suspended==False,Presence.user_id.in_(alive)).group_by(Presence.city)).all())
    live=dict(db.execute(select(Event.city,func.count()).where(Event.status=='live',Event.visibility=='public').group_by(Event.city)).all())
    return [{"interested_count": counts.get(c["id"], 0),"online":online.get(c["id"],0),"live_events":live.get(c["id"],0), **c} for c in catalog(db) if (include_disabled or c.get("public",True) and c.get("status")!="DISABLED")]


@router.get("/cities")
def public_cities(db=Depends(get_db)):
    return cities(db)


@router.get("/cities/interests")
def my_interests(u=Depends(current_user), db=Depends(get_db)):
    return list(
        db.scalars(select(CityInterest.city).where(CityInterest.user_id == u.id))
    )


@router.post("/cities/{city}/interest")
def join_interest(city: str, u=Depends(current_user), db=Depends(get_db)):
    from .expansion import add_interest
    return add_interest(db,u,city)


@router.delete("/cities/{city}/interest")
def leave_interest(city: str, u=Depends(current_user), db=Depends(get_db)):
    db.scalar(select(User.id).where(User.id == u.id).with_for_update())
    row = db.get(CityInterest, (u.id, city))
    if row:
        db.delete(row)
        db.add(Audit(actor_id=u.id, action="city_interest_left", target=city))
    return {"city": city, "joined": False}


@router.get("/passport")
def passport(u=Depends(current_user), db=Depends(get_db)):
    stamps = db.scalars(
        select(PassportStamp)
        .where(PassportStamp.user_id == u.id)
        .order_by(PassportStamp.created_at)
    )
    return {
        "kind": "virtual_city_passport",
        "stamps": [{"city": s.city, "earned_at": s.created_at} for s in stamps],
        "notice": "Stamps record virtual exploration, not verified physical travel.",
    }


@router.get("/people/search")
def search_people(
    q: str = Query(min_length=2, max_length=40),
    u=Depends(current_user),
    db=Depends(get_db),
):
    from .world import blocked, friends

    # SQL LIKE metacharacters are escaped; public discovery never returns email/location signals.
    pattern = (
        "%"
        + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        + "%"
    )
    if len(q.strip()) < 2:
        raise HTTPException(422, "Enter at least two non-space characters")
    candidates = db.scalars(
        select(User)
        .where(
            User.id != u.id,
            User.suspended == False,
            User.onboarded == True,
            User.username.ilike(pattern, escape="\\"),
        )
        .order_by(User.username)
        .limit(100)
    )
    result = []
    for p in candidates:
        if blocked(db, u.id, p.id):
            continue
        if p.privacy == "Friends Only" and not friends(db, u.id, p.id):
            continue
        if p.privacy in {"Ghost Mode", "Zone Mode", "Event Mode"}:
            continue
        result.append({"id": p.id, "username": p.username, "avatar": p.avatar})
        if len(result) == 20:
            break
    return result


@router.get("/world-provider")
def world_provider():
    return {
        "provider": "openstreetmap-bundled",
        "simulated": True,
        "photorealistic": False,
        "attribution": "© OpenStreetMap contributors · ODbL 1.0 · Stylised bounded districts",
        "external_provider_enabled": False,
        "notice": "Bundled licensed OpenStreetMap streets and footprints; stylised geometry within bounded playable districts.",
    }
