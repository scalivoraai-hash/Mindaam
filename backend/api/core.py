import re
import time
import secrets
import hashlib
from typing import Literal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, delete, func, or_
from .db import get_db, APP_ENV
from .models import *
from .auth import (
    current_user, login_result, request_token, COOKIE_NAME,
    require_admin,
    hash_password,
    check_password,
    session_token,
    public_user,
)
from .economy import credit, balance, config

router = APIRouter(prefix="/api")
from .locations import CITIES


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileFields(Strict):
    identity: Literal['Male','Female','Transgender','Non-binary','Prefer not to say','Custom / Other'] = 'Prefer not to say'
    custom_identity: str = Field(default='', max_length=60)
    show_identity: bool = False
    country: str = Field(default='', max_length=80)
    town: str = Field(default='', max_length=80)
    area: str = Field(default='', max_length=80)
    show_location: bool = False


class Register(Strict):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_ -]+$")
    adult: bool
    accepted_terms: bool
    profile: ProfileFields = Field(default_factory=ProfileFields)
    referral: str | None = None
    confirm_password: str | None = None
    accepted_privacy: bool | None = None


class Login(Strict):
    identifier: str | None = Field(default=None, max_length=254)
    email: str | None = Field(default=None, max_length=254)
    password: str = Field(max_length=128)


class Onboarding(Strict):
    city: str
    interests: list[str] = Field(default_factory=list, max_length=12)
    avatar: dict = Field(default_factory=dict)
    privacy: str = "City Mode"
    location_consent: bool = False
    analytics_consent: bool = False


def emit(db, u, kind, source=""):
    if u.analytics_consent:
        db.add(Analytics(user_id=u.id, kind=kind, source=source))


def notify(db, uid, kind, body, source=""):
    db.add(Notification(user_id=uid, kind=kind, body=body, source=source))


def serialize(row, exclude=()):
    return {
        c.name: getattr(row, c.name)
        for c in row.__table__.columns
        if c.name not in exclude
    }


def check_city(city):
    if city not in {c["id"] for c in CITIES}:
        raise HTTPException(422, "City not enabled")


@router.get("/config")
def get_config(db=Depends(get_db)):
    import os
    from .media_policy import settings

    return {
        "media_policy": settings(db),
        "cities": CITIES,
        "environment": APP_ENV,
        "simulated_world": True,
        "flags": {
            "liveface_enabled": bool(
                os.getenv("LIVEKIT_URL")
                and os.getenv("LIVEKIT_API_KEY")
                and os.getenv("LIVEKIT_API_SECRET")
            ),
            "payments_enabled": bool(os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_WEBHOOK_SECRET")),
            "physical_visit_enabled": bool(os.getenv("PULSEPOINT_SECRET")),
            "vehicles_enabled": True,
            "trains_enabled": False,
            "flights_enabled": False,
            "ai_assistant_enabled": False,
        },
        "vehicle_prices": config(
            db, "vehicle_prices", {"bike": 10, "scooter": 20, "car": 30}
        ),
        "daily_reward": config(
            db, "daily_rewards", {"schedule": [10, 15, 20, 25, 30, 40, 75]}
        ),
        "policy_version": "draft-1",
    }


@router.post("/auth/register", status_code=201)
def register(data: Register, request: Request, response: Response, db=Depends(get_db)):
    if request.headers.get("x-pulse-client") == "web" and (data.confirm_password is None or data.accepted_privacy is not True):
        raise HTTPException(422, "Password confirmation and privacy acceptance required")
    email = data.email.strip().lower()
    username = data.username.strip()
    if len(username) < 3:
        raise HTTPException(422, 'Username must contain at least three characters')
    if data.confirm_password is not None and data.confirm_password != data.password:
        raise HTTPException(422, 'Passwords do not match')
    if data.accepted_privacy is False:
        raise HTTPException(422, 'Privacy acceptance required')
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(422, "Enter a valid email")
    if not data.adult or not data.accepted_terms:
        raise HTTPException(422, "18+ confirmation and policy acceptance required")
    if db.scalar(
        select(User).where(or_(User.email == email, func.lower(func.trim(User.username)) == username.lower()))
    ):
        raise HTTPException(409, "Email or username already registered")
    user = User(
        email=email, username=username, password_hash=hash_password(data.password), profile=data.profile.model_dump()
    )
    db.add(user)
    db.flush()
    for document in ["age-18", "terms", "privacy", "community"]:
        db.add(Consent(user_id=user.id, document=document, accepted=True))
    if data.referral:
        parent = db.get(User, data.referral)
        if not parent or parent.suspended:
            raise HTTPException(422, "Referral unavailable")
        db.add(Referral(referred_id=user.id, referrer_id=parent.id))
    db.add(Audit(actor_id=user.id, action="registration", target=user.id))
    return login_result(db, user, request, response)


@router.post("/auth/login")
def login(data: Login, request: Request, response: Response, db=Depends(get_db)):
    identifier = (data.identifier or data.email or '').strip().lower()
    user = db.scalar(select(User).where(User.email == identifier if '@' in identifier else func.lower(func.trim(User.username)) == identifier))
    if (
        not user
        or not check_password(data.password, user.password_hash)
        or user.suspended
    ):
        raise HTTPException(401, "Invalid email, username or password")
    return login_result(db, user, request, response)


@router.post("/auth/logout")
def logout(
    request: Request, response: Response, u=Depends(current_user), authorization: str = Header(default=""), db=Depends(get_db)
):
    db.execute(
        delete(Session).where(
            Session.id == hashlib.sha256(request_token(request, authorization).encode()).hexdigest()
        )
    )
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.post("/auth/logout-all")
def logout_all(response: Response, u=Depends(current_user), db=Depends(get_db)):
    response.delete_cookie(COOKIE_NAME, path="/")
    db.execute(delete(Session).where(Session.user_id == u.id))
    db.execute(delete(Presence).where(Presence.user_id == u.id))
    return {"ok": True}


@router.get("/auth/sessions")
def sessions(u=Depends(current_user), db=Depends(get_db)):
    return [
        {"created_at": s.created_at, "expires_at": s.expires_at}
        for s in db.scalars(
            select(Session).where(
                Session.user_id == u.id, Session.expires_at > time.time()
            )
        )
    ]


@router.get("/me")
def me(u=Depends(current_user)):
    return public_user(u)


@router.put('/me/profile')
def update_profile(data: ProfileFields, u=Depends(current_user), db=Depends(get_db)):
    u.profile = {k:v.strip() if isinstance(v,str) else v for k,v in data.model_dump().items()}
    db.add(Audit(actor_id=u.id, action='profile.updated', target=u.id))
    return public_user(u)


@router.post("/onboarding")
def onboarding(data: Onboarding, u=Depends(current_user), db=Depends(get_db)):
    check_city(data.city)
    from .growth import select_starter,require_access
    if not u.onboarded:
        u.analytics_consent=data.analytics_consent
        select_starter(db,u,data.city,True)
    else:require_access(db,u,data.city)
    if data.privacy not in {
        "City Mode",
        "Zone Mode",
        "Friends Only",
        "Event Mode",
        "Ghost Mode",
    }:
        raise HTTPException(422, "Invalid privacy mode")
    if any(len(i) > 50 for i in data.interests) or len(str(data.avatar)) > 2000:
        raise HTTPException(422, "Profile too large")
    for document, accepted in [
        ("location", data.location_consent),
        ("analytics", data.analytics_consent),
    ]:
        db.add(Consent(user_id=u.id, document=document, accepted=accepted))
    for k, v in data.model_dump().items():
        setattr(u, k, v)
    if not u.onboarded:
        pack = config(db, "welcome_pack", {"credits": 50, "xp": 20, "bike_days": 7})
        credit(db, u.id, int(pack["credits"]), "welcome", "onboarding", "welcome")
        credit(
            db, u.id, int(pack["xp"]), "welcome", "onboarding", "welcome", currency="xp"
        )
        db.add(
            Entitlement(
                user_id=u.id,
                kind="bike",
                expires_at=time.time() + int(pack["bike_days"]) * 86400,
            )
        )
        u.onboarded = True
        notify(db, u.id, "welcome", "Welcome Pack added. Your city is waiting.")
    emit(db, u, "onboarding_completed")
    return public_user(u)


@router.get("/wallet")
def wallet(u=Depends(current_user), db=Depends(get_db)):
    rows = db.scalars(
        select(Ledger)
        .where(Ledger.user_id == u.id)
        .order_by(Ledger.created_at.desc())
        .limit(200)
    ).all()
    from .commerce import Perk, Offer

    perks = [
        {**serialize(p), "title": o.title}
        for p, o in db.execute(
            select(Perk, Offer)
            .join(Offer, Offer.id == Perk.offer_id)
            .where(Perk.user_id == u.id)
        )
    ]
    return {
        "credits": balance(db, u.id),
        "xp": balance(db, u.id, "xp"),
        "transactions": [serialize(x) for x in rows],
        "perks": perks,
        "entitlements": [
            serialize(e)
            for e in db.scalars(
                select(Entitlement).where(
                    Entitlement.user_id == u.id, Entitlement.expires_at > time.time()
                )
            )
        ],
    }


@router.post("/rewards/daily")
def daily(u=Depends(current_user), db=Depends(get_db)):
    if not u.onboarded:
        raise HTTPException(409, "Complete onboarding first")
    now = datetime.now(timezone.utc)
    day = now.date().isoformat()
    db.scalar(select(User).where(User.id == u.id).with_for_update())
    previous = db.scalars(
        select(Ledger)
        .where(Ledger.user_id == u.id, Ledger.kind == "daily")
        .order_by(Ledger.created_at.desc())
        .limit(7)
    ).all()
    streak = 0
    dates = {
        datetime.fromtimestamp(p.created_at, timezone.utc).date() for p in previous
    }
    from datetime import timedelta

    for n in range(1, 8):
        if now.date() - timedelta(days=n) in dates:
            streak += 1
        else:
            break
    schedule = config(db, "daily_rewards", {"schedule": [10, 15, 20, 25, 30, 40, 75]})[
        "schedule"
    ]
    existing = next((p for p in previous if p.source == day), None)
    if existing:
        return {
            "claimed": True,
            "amount": existing.amount,
            "credits": balance(db, u.id),
            "already_claimed": True,
        }
    amount = int(schedule[streak % len(schedule)])
    credit(db, u.id, amount, "daily", day, "daily:" + day)
    emit(db, u, "daily_reward_claimed", day)
    return {
        "claimed": True,
        "amount": amount,
        "credits": balance(db, u.id),
        "streak": streak + 1,
    }


@router.get("/notifications")
def notifications(u=Depends(current_user), db=Depends(get_db)):
    return [
        serialize(n)
        for n in db.scalars(
            select(Notification)
            .where(Notification.user_id == u.id)
            .order_by(Notification.created_at.desc())
            .limit(80)
        )
    ]


@router.get("/referrals")
def referrals(u=Depends(current_user), db=Depends(get_db)):
    rows = db.scalars(select(Referral).where(Referral.referrer_id == u.id)).all()
    return {
        "code": u.id,
        "link": "/?ref=" + u.id,
        "count": len(rows),
        "rewarded": sum(r.rewarded for r in rows),
        "milestone": "Verified account and first mission; rewards remain locked until verification.",
    }


@router.get("/privacy/export")
def export(u=Depends(current_user), db=Depends(get_db)):
    from .identity import commerce_export
    from .discovery import PassportStamp, CityInterest
    from .transit import Ticket
    from .operations import AdEnquiry
    from .mobility import RentalLease,RentalConsent
    from .gifts import GiftDelivery,Reaction
    from .expansion import DemandShare,DemandShareAction
    from .business_spatial import BusinessInteraction

    return {
        'rentals':[serialize(r) for r in db.scalars(select(RentalLease).where(RentalLease.user_id==u.id))],
        'rental_consents':[serialize(r) for r in db.scalars(select(RentalConsent).where(RentalConsent.user_id==u.id))],
        'gift_receipts':[serialize(r) for r in db.scalars(select(GiftDelivery).where((GiftDelivery.sender_id==u.id)|(GiftDelivery.recipient_id==u.id)))],
        'city_demand_shares':[serialize(r) for r in db.scalars(select(DemandShareAction).join(DemandShare).where(DemandShare.user_id==u.id))],
        'business_interactions':[serialize(r) for r in db.scalars(select(BusinessInteraction).where(BusinessInteraction.user_id==u.id))],
        "commerce": commerce_export(db, u),
        "transport_tickets": [serialize(x) for x in db.scalars(select(Ticket).where(Ticket.user_id==u.id))],
        "advertising_enquiries": [serialize(x) for x in db.scalars(select(AdEnquiry).where(AdEnquiry.user_id==u.id))],
        "passport": [
            serialize(x)
            for x in db.scalars(
                select(PassportStamp).where(PassportStamp.user_id == u.id)
            )
        ],
        "city_interests": [
            serialize(x)
            for x in db.scalars(
                select(CityInterest).where(CityInterest.user_id == u.id)
            )
        ],
        "profile": {**public_user(u), "email": u.email},
        "consents": [
            serialize(c)
            for c in db.scalars(select(Consent).where(Consent.user_id == u.id))
        ],
        "wallet": wallet(u, db),
        "sent_messages": [
            serialize(m)
            for m in db.scalars(select(Message).where(Message.sender == u.id))
        ],
        "notice": "Commerce records available through business and perks APIs; full portability review remains required.",
    }


@router.delete("/me")
def delete_me(u=Depends(current_user), db=Depends(get_db)):
    from .identity import anonymise_commerce
    from .discovery import PassportStamp, CityInterest

    anonymise_commerce(db, u)
    from .mobility import finish as finish_rental
    from .business_spatial import BusinessInteraction,BusinessMember
    from .gifts import Reaction
    from .expansion import DemandShare,DemandShareAction
    from .civic import InteriorVisit
    finish_rental(db,u)
    for model in [BusinessInteraction,BusinessMember,Reaction,InteriorVisit]:db.execute(delete(model).where(model.user_id==u.id))
    codes=select(DemandShare.code).where(DemandShare.user_id==u.id)
    db.execute(delete(DemandShareAction).where(DemandShareAction.code.in_(codes)))
    db.execute(delete(DemandShare).where(DemandShare.user_id==u.id))
    from .operations import AdEnquiry,UserActivity,AdInteraction
    for enquiry in db.scalars(select(AdEnquiry).where(AdEnquiry.user_id==u.id)):
        enquiry.contact_name='[deleted]';enquiry.email='deleted@invalid.local';enquiry.phone='';enquiry.website='';enquiry.message='[deleted]'
    for model in [UserActivity,AdInteraction]:db.execute(delete(model).where(model.user_id==u.id))
    for model in [PassportStamp, CityInterest]:
        db.execute(delete(model).where(model.user_id == u.id))
    db.execute(delete(Session).where(Session.user_id == u.id))
    db.execute(delete(Presence).where(Presence.user_id == u.id))
    u.email = "deleted-" + u.id + "@invalid.local"
    u.username = "deleted-" + u.id.replace("-", "")[:24]
    u.password_hash = hash_password(secrets.token_urlsafe(50))
    u.suspended = True
    u.avatar = {}
    u.profile = {}
    from .talk import TalkMessage
    for m in db.scalars(select(TalkMessage).where(TalkMessage.sender == u.id)):
        m.body = "[deleted]"
    u.interests = []
    u.location_consent = False
    u.analytics_consent = False
    for m in db.scalars(select(Message).where(Message.sender == u.id)):
        m.body = "[deleted]"
    db.add(Audit(actor_id=u.id, action="account.anonymised", target=u.id))
    return {
        "ok": True,
        "notice": "Account anonymised. Ledger and audit records retained; full retention policy must be approved before public release.",
    }


@router.get("/admin/overview")
def admin_overview(u=Depends(require_admin), db=Depends(get_db)):
    from .commerce import Business

    return {
        "users": db.scalar(select(func.count()).select_from(User)),
        "businesses": db.scalar(select(func.count()).select_from(Business)),
        "transactions": db.scalar(select(func.count()).select_from(Ledger)),
        "reports": db.scalar(
            select(func.count()).select_from(Report).where(Report.status == "open")
        ),
        "online": db.scalar(
            select(func.count())
            .select_from(Presence)
            .where(Presence.updated_at > time.time() - 45)
        ),
    }


@router.get("/admin/users")
def admin_users(u=Depends(require_admin), db=Depends(get_db)):
    return [
        {**public_user(x), "suspended": x.suspended, "email": x.email}
        for x in db.scalars(select(User).limit(200))
    ]


class Suspension(Strict):
    suspended: bool


@router.patch("/admin/users/{user_id}")
def suspend(
    user_id: str, data: Suspension, u=Depends(require_admin), db=Depends(get_db)
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if target.role in {"admin", "super_admin"}:
        raise HTTPException(
            409, "Admin suspension requires separate operational review"
        )
    target.suspended = data.suspended
    if data.suspended:
        db.execute(delete(Session).where(Session.user_id == user_id))
        db.execute(delete(Presence).where(Presence.user_id == user_id))
    db.add(
        Audit(
            actor_id=u.id,
            action="user.suspend",
            target=user_id,
            details=data.model_dump(),
        )
    )
    return public_user(target)


@router.get("/admin/reports")
def admin_reports(u=Depends(require_admin), db=Depends(get_db)):
    return [
        serialize(r)
        for r in db.scalars(
            select(Report).order_by(Report.created_at.desc()).limit(200)
        )
    ]


class Resolution(Strict):
    action: str = Field(min_length=3, max_length=500)


@router.post("/admin/reports/{report_id}/resolve")
def resolve(
    report_id: str, data: Resolution, u=Depends(require_admin), db=Depends(get_db)
):
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    r.status = "resolved"
    db.add(
        Audit(
            actor_id=u.id,
            action="report.resolve",
            target=report_id,
            details=data.model_dump(),
        )
    )
    return serialize(r)


@router.get("/admin/audit")
def audits(u=Depends(require_admin), db=Depends(get_db)):
    return [
        serialize(a)
        for a in db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(200))
    ]


@router.get("/admin/config/{key}")
def read_config(key: str, u=Depends(require_admin), db=Depends(get_db)):
    row = db.get(Config, key)
    return {"key": key, "value": row.value if row else None}


class Configuration(Strict):
    value: dict


@router.put("/admin/config/{key}")
def write_config(
    key: str, data: Configuration, u=Depends(require_admin), db=Depends(get_db)
):
    schemas = {
        "daily_rewards": {"schedule"},
        "welcome_pack": {"credits", "xp", "bike_days"},
        "vehicle_prices": {"bike", "scooter", "car"},
    }
    if key not in schemas or set(data.value) != schemas[key]:
        raise HTTPException(422, "Unknown configuration or invalid keys")
    values = (
        data.value["schedule"] if key == "daily_rewards" else list(data.value.values())
    )
    if (
        not isinstance(values, list)
        or not 1 <= len(values) <= 31
        or any(type(v) != int or not 0 <= v <= 10000 for v in values)
    ):
        raise HTTPException(422, "Invalid configuration values")
    row = db.get(Config, key)
    if row:
        row.value = data.value
        row.updated_at = time.time()
    else:
        db.add(Config(key=key, value=data.value))
    db.add(Audit(actor_id=u.id, action="config.update", target=key, details=data.value))
    return {"key": key, "value": data.value}


@router.get("/businesses/{business_id}/manage")
def manage_store(business_id: str, u=Depends(current_user), db=Depends(get_db)):
    from .commerce import tenant, Product, Offer, Campaign, record

    b = tenant(db, business_id, u)
    return {
        "business": record(b),
        "products": [
            record(x)
            for x in db.scalars(select(Product).where(Product.business_id == b.id))
        ],
        "offers": [
            record(x)
            for x in db.scalars(select(Offer).where(Offer.business_id == b.id))
        ],
        "campaigns": [
            record(x)
            for x in db.scalars(select(Campaign).where(Campaign.business_id == b.id))
        ],
    }

from .geography import district

@router.get('/world-preview/{city}')
def world_preview(city: str, db=Depends(get_db)):
    """Public catalogue geometry only; never presence, private profiles or rewards."""
    check_city(city)
    objects=db.scalars(select(Collectible).where(Collectible.city==city,Collectible.active==True,Collectible.starts_at<=time.time(),Collectible.ends_at>time.time())).all()
    return {'city':city,'zone':next(c['zone'] for c in CITIES if c['id']==city),'simulated':True,'preview':True,'collectibles':[{'id':c.id,'title':c.title,'kind':c.kind,'x':c.x,'z':c.z} for c in objects],'players':[],'position':{'x':district(city)['spawn'][0],'z':district(city)['spawn'][1]}}


@router.get('/auth/providers')
def auth_providers():
    from .oauth import providers
    return {**providers(), 'emailPassword': True}

class ChangePassword(Strict):
    current_password: str = Field(max_length=128)
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str

@router.post('/auth/change-password')
def change_password(data: ChangePassword, response: Response, u=Depends(current_user), db=Depends(get_db)):
    if not check_password(data.current_password, u.password_hash):
        raise HTTPException(401, 'Current password is incorrect')
    if data.password != data.confirm_password:
        raise HTTPException(422, 'Passwords do not match')
    u.must_change_password=False
    u.password_hash = hash_password(data.password)
    db.execute(delete(Session).where(Session.user_id == u.id))
    response.delete_cookie(COOKIE_NAME, path='/')
    db.add(Audit(actor_id=u.id, action='identity.password_changed', target=u.id))
    return {'changed': True}
