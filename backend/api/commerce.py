"""Tenant-isolated commerce and ledger-backed rewards; no synthetic funding."""

import base64
import hashlib
import hmac
import json
import math
import os
import secrets
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    select,
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .db import Base, get_db
from .auth import current_user
from .models import User
from .economy import credit, config

router = APIRouter(prefix="/api", tags=["commerce"])


def uid():
    return str(uuid.uuid4())


def now():
    return time.time()


class Business(Base):
    __tablename__ = "businesses"
    id = Column(String, primary_key=True, default=uid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    city = Column(String(80), nullable=False, index=True)
    address = Column(String(300), nullable=False)
    description = Column(Text, default="")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="pending")
    funds = Column(Integer, nullable=False, default=0)
    signage = Column(JSON, nullable=False, default=dict)
    created_at = Column(Float, default=now)
    __table_args__ = (CheckConstraint("funds >= 0"),)


class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True, default=uid)
    business_id = Column(
        String, ForeignKey("businesses.id"), nullable=False, index=True
    )
    name = Column(String(120), nullable=False)
    description = Column(Text, default="")
    kind = Column(String, nullable=False)
    price_pence = Column(Integer, nullable=False)


class Offer(Base):
    __tablename__ = "offers"
    id = Column(String, primary_key=True, default=uid)
    business_id = Column(
        String, ForeignKey("businesses.id"), nullable=False, index=True
    )
    title = Column(String(120), nullable=False)
    description = Column(Text, default="")
    cost_credits = Column(Integer, nullable=False)
    active = Column(Integer, default=1)


class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(String, primary_key=True, default=uid)
    business_id = Column(
        String, ForeignKey("businesses.id"), nullable=False, index=True
    )
    title = Column(String(120), nullable=False)
    kind = Column(String, nullable=False, default="visit")
    reward_credits = Column(Integer, nullable=False)
    budget_credits = Column(Integer, nullable=False)
    spent_credits = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="draft")
    offer_id = Column(String, ForeignKey("offers.id"), nullable=True)
    __table_args__ = (
        CheckConstraint("spent_credits >= 0 AND spent_credits <= budget_credits"),
    )


class FundingLedger(Base):
    __tablename__ = "funding_ledger"
    id = Column(String, primary_key=True, default=uid)
    business_id = Column(
        String, ForeignKey("businesses.id"), nullable=False, index=True
    )
    amount = Column(Integer, nullable=False)
    kind = Column(String, nullable=False)
    source = Column(String, nullable=False)
    key = Column(String, unique=True, nullable=False)
    created_at = Column(Float, default=now)


class CommerceAudit(Base):
    __tablename__ = "commerce_audit"
    id = Column(String, primary_key=True, default=uid)
    actor_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    created_at = Column(Float, default=now)


class PulsePoint(Base):
    __tablename__ = "pulsepoints"
    id = Column(String, primary_key=True, default=uid)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    expires_at = Column(Float, nullable=False)
    consumed_at = Column(Float, nullable=True)


class Visit(Base):
    __tablename__ = "verified_visits"
    id = Column(String, primary_key=True, default=uid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    business_id = Column(
        String, ForeignKey("businesses.id"), nullable=False, index=True
    )
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False)
    pulsepoint_id = Column(String, unique=True, nullable=False)
    day = Column(Integer, nullable=False)
    reward = Column(Integer, nullable=False)
    created_at = Column(Float, default=now)
    __table_args__ = (UniqueConstraint("user_id", "business_id", "day"),)


class Perk(Base):
    __tablename__ = "perks"
    id = Column(String, primary_key=True, default=uid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    offer_id = Column(String, ForeignKey("offers.id"), nullable=False)
    source_key = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False, default="issued")
    created_at = Column(Float, default=now)


class StoreVisit(Base):
    __tablename__ = "store_visits"
    id = Column(String, primary_key=True, default=uid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False)
    day = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "business_id", "day"),)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True, default=uid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=True)
    sku = Column(String, nullable=False)
    amount_pence = Column(Integer, nullable=False)
    credits = Column(Integer, nullable=False)
    provider_id = Column(String, unique=True, nullable=True)
    checkout_url = Column(Text, nullable=True)
    intent_id = Column(String, unique=True, index=True, nullable=True)
    refunded_pence = Column(Integer, nullable=False, default=0, server_default='0')
    reversed_credits = Column(Integer, nullable=False, default=0, server_default='0')
    dispute_status = Column(String, nullable=True)
    dispute_pence = Column(Integer, nullable=False, default=0, server_default='0')
    dispute_updated = Column(Float, nullable=False, default=0, server_default='0')
    status = Column(String, default="pending", nullable=False)
    request_key = Column(String, unique=True, nullable=False)
    created_at = Column(Float, default=now, index=True)


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False)
    created_at = Column(Float, default=now)


for immutable_model in (FundingLedger, CommerceAudit, PaymentEvent):

    def immutable(*args):
        raise ValueError("Ledger/audit rows are immutable")

    event.listen(immutable_model, "before_update", immutable)
    event.listen(immutable_model, "before_delete", immutable)


def audit(db, actor, action, obj):
    db.add(CommerceAudit(actor_id=actor.id, action=action, object_id=obj))


def tenant(db, id, user, lock=False):
    from .business_spatial import BusinessMember
    q = select(Business).where(Business.id == id, (Business.owner_id == user.id) | Business.id.in_(select(BusinessMember.business_id).where(BusinessMember.user_id==user.id)))
    business = db.scalar(q.with_for_update() if lock else q)
    if not business:
        raise HTTPException(404, "Business not found")
    return business


def admin(user):
    if user.role not in ["admin","super_admin"]:
        raise HTTPException(403, "Administrator required")


def public_business(b):
    return {
        k: getattr(b, k)
        for k in ("id", "name", "city", "address", "description", "status", "signage")
    }


def record(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def fund(db, business, amount, kind, source, key):
    if db.scalar(select(FundingLedger).where(FundingLedger.key == key)):
        return
    if business.funds + amount < 0:
        raise HTTPException(409, "Insufficient funded campaign credits")
    business.funds += amount
    db.add(
        FundingLedger(
            business_id=business.id, amount=amount, kind=kind, source=source, key=key
        )
    )
    db.flush()


class BusinessInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=80)
    address: str = Field(min_length=3, max_length=300)
    description: str = Field(default="", max_length=3000)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


@router.post("/businesses")
def create_business(
    data: BusinessInput, user=Depends(current_user), db: Session = Depends(get_db)
):
    b = Business(owner_id=user.id, **data.model_dump())
    db.add(b)
    db.flush()
    audit(db, user, "business.created", b.id)
    return public_business(b)


@router.get("/business/mine")
def my_businesses(user=Depends(current_user), db: Session = Depends(get_db)):
    from .business_spatial import BusinessMember
    return [
        dict(public_business(b), funds=b.funds)
        for b in db.scalars(select(Business).where((Business.owner_id == user.id) | Business.id.in_(select(BusinessMember.business_id).where(BusinessMember.user_id==user.id))))
    ]


@router.get("/businesses")
def businesses(city: str | None = None, db: Session = Depends(get_db)):
    q = select(Business).where(Business.status == "verified")
    if city:
        q = q.where(Business.city == city)
    return [public_business(b) for b in db.scalars(q.limit(100))]


@router.get("/businesses/{business_id}")
def storefront(business_id: str, db: Session = Depends(get_db)):
    b = db.get(Business, business_id)
    if not b or b.status != "verified":
        raise HTTPException(404, "Store unavailable")
    return {
        "business": public_business(b),
        "products": [
            record(x)
            for x in db.scalars(select(Product).where(Product.business_id == b.id))
        ],
        "offers": [
            record(x)
            for x in db.scalars(
                select(Offer).where(Offer.business_id == b.id, Offer.active == 1)
            )
        ],
        "campaigns": [
            record(x)
            for x in db.scalars(
                select(Campaign).where(
                    Campaign.business_id == b.id, Campaign.status == "active"
                )
            )
        ],
    }


@router.post("/businesses/{business_id}/visit")
def virtual_visit(
    business_id: str, user=Depends(current_user), db: Session = Depends(get_db)
):
    b = db.get(Business, business_id)
    if not b or b.status != "verified":
        raise HTTPException(404, "Store unavailable")
    day = int(now() // 86400)
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    if not db.scalar(
        select(StoreVisit).where(
            StoreVisit.user_id == user.id,
            StoreVisit.business_id == b.id,
            StoreVisit.day == day,
        )
    ):
        db.add(StoreVisit(user_id=user.id, business_id=b.id, day=day))
    return {"recorded": True}


class ProductInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=3000)
    kind: str = Field(pattern="^(product|service)$")
    price_pence: int = Field(ge=0, le=10000000)


@router.post("/businesses/{business_id}/products")
def add_product(
    business_id: str,
    data: ProductInput,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    tenant(db, business_id, user)
    p = Product(business_id=business_id, **data.model_dump())
    db.add(p)
    db.flush()
    audit(db, user, "product.created", p.id)
    return record(p)


class OfferInput(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=3000)
    cost_credits: int = Field(ge=0, le=100000)


@router.post("/businesses/{business_id}/offers")
def add_offer(
    business_id: str,
    data: OfferInput,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    tenant(db, business_id, user)
    o = Offer(business_id=business_id, **data.model_dump())
    db.add(o)
    db.flush()
    audit(db, user, "offer.created", o.id)
    return record(o)


class CampaignInput(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    kind: str = Field(default="visit", pattern="^visit$")
    reward_credits: int = Field(ge=1, le=1000)
    budget_credits: int = Field(ge=1, le=1000000)
    offer_id: str | None = None


@router.post("/businesses/{business_id}/campaigns")
def add_campaign(
    business_id: str,
    data: CampaignInput,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    tenant(db, business_id, user)
    if data.budget_credits < data.reward_credits:
        raise HTTPException(422, "Budget must cover at least one reward")
    if data.offer_id and not db.scalar(
        select(Offer).where(Offer.id == data.offer_id, Offer.business_id == business_id)
    ):
        raise HTTPException(404, "Offer not found")
    c = Campaign(business_id=business_id, **data.model_dump())
    db.add(c)
    db.flush()
    audit(db, user, "campaign.created", c.id)
    return record(c)


@router.post("/campaigns/{campaign_id}/publish")
def publish(
    campaign_id: str, user=Depends(current_user), db: Session = Depends(get_db)
):
    c = db.scalar(select(Campaign).where(Campaign.id == campaign_id).with_for_update())
    if not c:
        raise HTTPException(404, "Campaign not found")
    b = tenant(db, c.business_id, user, True)
    if b.status != "verified":
        raise HTTPException(409, "Business verification required")
    if c.status == "active":
        return record(c)
    if c.status != "draft":
        raise HTTPException(409, "Campaign cannot be published")
    fund(db, b, -c.budget_credits, "campaign.reserve", c.id, "reserve:" + c.id)
    c.status = "active"
    audit(db, user, "campaign.published", c.id)
    return record(c)


@router.post("/campaigns/{campaign_id}/close")
def close_campaign(
    campaign_id: str, user=Depends(current_user), db: Session = Depends(get_db)
):
    c = db.scalar(select(Campaign).where(Campaign.id == campaign_id).with_for_update())
    if not c:
        raise HTTPException(404, "Campaign not found")
    b = tenant(db, c.business_id, user, True)
    if c.status == "active":
        fund(
            db,
            b,
            c.budget_credits - c.spent_credits,
            "campaign.release",
            c.id,
            "release:" + c.id,
        )
    c.status = "closed"
    audit(db, user, "campaign.closed", c.id)
    return record(c)


@router.get("/campaigns")
def active_campaigns(db: Session = Depends(get_db)):
    return [
        dict(record(c), business_name=b.name, city=b.city)
        for c, b in db.execute(
            select(Campaign, Business)
            .join(Business, Campaign.business_id == Business.id)
            .where(Campaign.status == "active", Business.status == "verified")
            .limit(100)
        )
    ]


def signing_key():
    key = os.getenv("PULSEPOINT_SECRET", "")
    if len(key) < 32:
        raise HTTPException(
            503, "PulsePoint verification unavailable: signing secret not configured"
        )
    return key.encode()


def sign(payload):
    body = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )
    return (
        body + "." + hmac.new(signing_key(), body.encode(), hashlib.sha256).hexdigest()
    )


def unsign(token):
    key = signing_key()
    try:
        body, sig = token.split(".")
        if not hmac.compare_digest(
            sig, hmac.new(key, body.encode(), hashlib.sha256).hexdigest()
        ):
            raise ValueError()
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if data["exp"] < now():
            raise ValueError()
        return data
    except (ValueError, KeyError, TypeError):
        raise HTTPException(400, "Invalid or expired PulsePoint")


class QRInput(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)


@router.post("/campaigns/{campaign_id}/pulsepoint")
def pulsepoint(
    campaign_id: str,
    data: QRInput,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    signing_key()
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    b = tenant(db, c.business_id, user)
    if c.status != "active" or b.status != "verified":
        raise HTTPException(409, "Campaign inactive")
    if not db.get(User, data.user_id):
        raise HTTPException(404, "Consumer not found")
    if data.user_id == user.id:
        raise HTTPException(409, "Owners cannot claim their own campaigns")
    p = PulsePoint(campaign_id=c.id, user_id=data.user_id, expires_at=now() + 120)
    db.add(p)
    db.flush()
    return {
        "token": sign({"id": p.id, "user": p.user_id, "exp": p.expires_at}),
        "expires_at": p.expires_at,
    }


class VerifyInput(BaseModel):
    token: str = Field(min_length=10, max_length=2000)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    accuracy_m: float = Field(gt=0, le=50, allow_inf_nan=False)
    consent: bool


def distance(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    dp = p2 - p1
    dl = math.radians(d - b)
    return (
        6371000
        * 2
        * math.asin(
            min(
                1,
                math.sqrt(
                    math.sin(dp / 2) ** 2
                    + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
                ),
            )
        )
    )


@router.post("/visits/verify")
def verify_visit(
    data: VerifyInput, user=Depends(current_user), db: Session = Depends(get_db)
):
    if not data.consent:
        raise HTTPException(422, "Explicit location consent required")
    claims = unsign(data.token)
    if claims["user"] != user.id:
        raise HTTPException(403, "PulsePoint belongs to another user")
    p = db.scalar(
        select(PulsePoint).where(PulsePoint.id == claims["id"]).with_for_update()
    )
    if not p or p.user_id != user.id or p.expires_at < now():
        raise HTTPException(400, "Invalid or expired PulsePoint")
    if p.consumed_at:
        raise HTTPException(409, "PulsePoint already used")
    c = db.scalar(
        select(Campaign).where(Campaign.id == p.campaign_id).with_for_update()
    )
    b = db.get(Business, c.business_id)
    if c.status != "active" or b.status != "verified":
        raise HTTPException(409, "Campaign inactive")
    if b.owner_id == user.id:
        raise HTTPException(409, "Owners cannot claim their own campaign")
    if (
        distance(data.latitude, data.longitude, b.latitude, b.longitude)
        + data.accuracy_m
        > 100
    ):
        raise HTTPException(422, "Location cannot be verified within 100 metres")
    day = int(now() // 86400)
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    if db.scalar(
        select(Visit).where(
            Visit.user_id == user.id, Visit.business_id == b.id, Visit.day == day
        )
    ):
        raise HTTPException(409, "One physical reward per business per UTC day")
    if c.spent_credits + c.reward_credits > c.budget_credits:
        raise HTTPException(409, "Campaign budget exhausted")
    v = Visit(
        user_id=user.id,
        business_id=b.id,
        campaign_id=c.id,
        pulsepoint_id=p.id,
        day=day,
        reward=c.reward_credits,
    )
    db.add(v)
    db.flush()
    c.spent_credits += c.reward_credits
    p.consumed_at = now()
    credit(db, user.id, c.reward_credits, "visit", c.id, "visit:" + p.id)
    db.add(
        FundingLedger(
            business_id=b.id,
            amount=0,
            kind="campaign.award",
            source=v.id,
            key="award:" + p.id,
        )
    )
    if c.offer_id:
        db.add(Perk(user_id=user.id, offer_id=c.offer_id, source_key="visit:" + p.id))
    audit(db, user, "visit.qr_geofence_verified", v.id)
    return {
        "visit_id": v.id,
        "credits_awarded": c.reward_credits,
        "verification": "merchant QR and consented device geofence",
        "precise_location_stored": False,
    }


@router.get("/perks")
def perks(user=Depends(current_user), db: Session = Depends(get_db)):
    return [
        dict(
            record(p),
            title=o.title,
            description=o.description,
            business_id=o.business_id,
        )
        for p, o in db.execute(
            select(Perk, Offer)
            .join(Offer, Perk.offer_id == Offer.id)
            .where(Perk.user_id == user.id)
        )
    ]


class RedeemInput(BaseModel):
    request_id: str = Field(default_factory=uid, min_length=8, max_length=100)


@router.post("/offers/{offer_id}/redeem")
def redeem(
    offer_id: str,
    data: RedeemInput,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    key = "redeem:" + user.id + ":" + offer_id + ":" + data.request_id
    prior = db.scalar(select(Perk).where(Perk.source_key == key))
    if prior:
        return record(prior)
    o = db.get(Offer, offer_id)
    if not o or not o.active or db.get(Business, o.business_id).status != "verified":
        raise HTTPException(404, "Offer unavailable")
    if o.cost_credits:
        credit(db, user.id, -o.cost_credits, "perk", o.id, key)
    p = Perk(user_id=user.id, offer_id=o.id, source_key=key)
    db.add(p)
    db.flush()
    audit(db, user, "perk.issued", p.id)
    return record(p)


@router.post("/perks/{perk_id}/use")
def use_perk(perk_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    p = db.scalar(select(Perk).where(Perk.id == perk_id).with_for_update())
    if not p:
        raise HTTPException(404, "Perk not found")
    o = db.get(Offer, p.offer_id)
    tenant(db, o.business_id, user)
    if p.status != "issued":
        raise HTTPException(409, "Perk already used")
    p.status = "used"
    audit(db, user, "perk.used", p.id)
    return record(p)


@router.get("/businesses/{business_id}/analytics")
def analytics(
    business_id: str, user=Depends(current_user), db: Session = Depends(get_db)
):
    b = tenant(db, business_id, user)
    count = lambda m, *criteria: (
        db.scalar(select(func.count()).select_from(m).where(*criteria)) or 0
    )
    campaigns = list(db.scalars(select(Campaign).where(Campaign.business_id == b.id)))
    return {
        "business": public_business(b),
        "available_funds": b.funds,
        "virtual_visitors": count(StoreVisit, StoreVisit.business_id == b.id),
        "verified_visits": count(Visit, Visit.business_id == b.id),
        "credits_awarded": db.scalar(
            select(func.sum(Visit.reward)).where(Visit.business_id == b.id)
        )
        or 0,
        "perks_used": db.scalar(
            select(func.count())
            .select_from(Perk)
            .join(Offer, Perk.offer_id == Offer.id)
            .where(Offer.business_id == b.id, Perk.status == "used")
        )
        or 0,
        "campaigns": [record(c) for c in campaigns],
        "funding_ledger": [
            record(x)
            for x in db.scalars(
                select(FundingLedger)
                .where(FundingLedger.business_id == b.id)
                .order_by(FundingLedger.created_at.desc())
                .limit(100)
            )
        ],
        "measurement_note": "Virtual visitors are unique authenticated visitors per UTC day; physical visits use merchant-issued QR plus browser geofence, not device attestation.",
    }


@router.get("/admin/businesses")
def admin_businesses(user=Depends(current_user), db: Session = Depends(get_db)):
    admin(user)
    return [
        dict(public_business(b), owner_id=b.owner_id)
        for b in db.scalars(select(Business).limit(200))
    ]


class Approval(BaseModel):
    approved: bool


@router.post("/admin/businesses/{business_id}/verify")
def verify_business(
    business_id: str,
    data: Approval,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    admin(user)
    b = db.get(Business, business_id)
    if not b:
        raise HTTPException(404, "Business not found")
    if b.owner_id == user.id:
        raise HTTPException(409, "Independent administrator verification required")
    b.status = "verified" if data.approved else "rejected"
    audit(db, user, "business." + b.status, b.id)
    return public_business(b)


SKUS = {
    "credits_500": {"amount": 499, "credits": 500, "name": "500 Pulse Credits"},
    "campaign_1000": {
        "amount": 1000,
        "credits": 1000,
        "name": "1000 campaign funding credits",
    },
}


class CheckoutInput(BaseModel):
    sku: str
    business_id: str | None = None
    expected_amount: int | None = Field(default=None,ge=1,le=10000000)
    request_id: str = Field(default_factory=uid, min_length=8, max_length=100)


@router.get('/payments/{payment_id}/status')
def payment_status(payment_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    p = db.scalar(select(Payment).where(Payment.id == payment_id, Payment.user_id == user.id))
    if not p:
        raise HTTPException(404, 'Payment not found')
    return {'id': p.id, 'status': p.status, 'credits': p.credits, 'amount_pence': p.amount_pence, 'currency': 'GBP'}


@router.post("/payments/checkout")
def checkout(
    data: CheckoutInput, user=Depends(current_user), db: Session = Depends(get_db)
):
    import stripe

    secret = os.getenv("STRIPE_SECRET_KEY", "")
    origin = os.getenv("PUBLIC_APP_URL", "http://localhost:3000").rstrip("/")
    from .payment_settlement import configured
    if not configured():
        raise HTTPException(503, "Payments unavailable: secure Stripe configuration is incomplete")
    from .credit_catalog import catalogue
    catalog = catalogue(db)
    if not catalog:
        raise HTTPException(503, "Commercial catalogue is not configured")
    if data.sku not in catalog:
        raise HTTPException(422, "Unknown product")
    if data.sku.startswith("campaign_"):
        b = tenant(db, data.business_id, user)
        if b.status != "verified":
            raise HTTPException(409, "Business verification required")
    elif data.business_id:
        raise HTTPException(422, "Consumer credits cannot fund a business")
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    key = user.id + ":" + data.request_id
    p = db.scalar(select(Payment).where(Payment.request_key == key))
    if p:
        if p.sku != data.sku or p.business_id != data.business_id:
            raise HTTPException(409, "Idempotency key reused for different purchase")
        return {"url": p.checkout_url, "payment_id": p.id}
    sku = catalog[data.sku]
    if data.expected_amount is not None and data.expected_amount!=sku.get("amount"):
        raise HTTPException(409,"The price changed. Review the Credit pack before continuing.")
    if (
        not isinstance(sku, dict)
        or not isinstance(sku.get("amount"), int)
        or not isinstance(sku.get("credits"), int)
        or not 1 <= sku["amount"] <= 10000000
        or not 1 <= sku["credits"] <= 1000000
        or not isinstance(sku.get("name"), str)
    ):
        raise HTTPException(503, "Commercial catalogue contains invalid pricing")
    p = Payment(
        id=str(uuid.uuid5(uuid.NAMESPACE_URL, "pulseworld-payment:" + key)),
        user_id=user.id,
        business_id=data.business_id,
        sku=data.sku,
        amount_pence=sku["amount"],
        credits=sku["credits"],
        request_key=key,
    )
    db.add(p)
    db.flush()
    try:
        s = stripe.checkout.Session.create(
            api_key=secret,
            idempotency_key="pulse:" + hashlib.sha256(key.encode()).hexdigest(),
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "gbp",
                        "unit_amount": sku["amount"],
                        "product_data": {"name": sku["name"]},
                    },
                    "quantity": 1,
                }
            ],
            metadata={"payment_id": p.id},
            payment_intent_data={"metadata": {"payment_id": p.id}},
            success_url=origin + "/wallet?checkout=returned",
            cancel_url=origin + "/wallet?checkout=cancelled",
        )
    except stripe.StripeError:
        raise HTTPException(
            502, "Payment provider unavailable; retry with the same request ID"
        )
    p.provider_id = s.id
    p.checkout_url = s.url
    return {"url": s.url, "payment_id": p.id}


@router.post("/payments/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    import stripe

    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(503, "Webhook unavailable: signing secret not configured")
    body = await request.body()
    if len(body) > 262144:
        raise HTTPException(413, "Webhook too large")
    try:
        e = stripe.Webhook.construct_event(
            body, request.headers.get("stripe-signature", ""), secret, tolerance=300
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, "Invalid webhook signature")
    envelope = json.loads(body)
    if os.getenv('APP_ENV', 'local') != 'production' and envelope.get('livemode') is True:
        raise HTTPException(400, 'Live payment events are not accepted in this environment')
    if db.get(PaymentEvent, e.id):
        return {"received": True, "duplicate": True}
    try:
        with db.begin_nested():
            db.add(PaymentEvent(id=e.id, event_type=e.type))
            db.flush()
    except IntegrityError:
        return {"received": True, "duplicate": True}
    obj = json.loads(body)["data"]["object"]
    if e.type in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
        "checkout.session.expired",
        "checkout.session.async_payment_failed",
    ):
        p = db.scalar(select(Payment).where(Payment.provider_id == obj['id']))
        if not p:
            raise HTTPException(
                409, "Unknown checkout session; retry after checkout persistence"
            )
        db.scalar(select(User.id).where(User.id == p.user_id).with_for_update())
        p = db.scalar(select(Payment).where(Payment.id == p.id).with_for_update().execution_options(populate_existing=True))
        if obj.get("metadata", {}).get("payment_id") != p.id:
            raise HTTPException(400, "Payment metadata mismatch")
        intent = obj.get('payment_intent')
        if intent:
            if not isinstance(intent, str) or (p.intent_id and p.intent_id != intent):
                raise HTTPException(400, 'Payment intent mismatch')
            p.intent_id = intent
        if e.type in (
            "checkout.session.expired",
            "checkout.session.async_payment_failed",
        ):
            if p.status != "paid":
                p.status = "failed"
        elif obj.get("payment_status") == "paid" and p.status != "paid":
            if (
                obj.get("amount_total") != p.amount_pence
                or obj.get("currency") != "gbp"
            ):
                raise HTTPException(400, "Payment amount mismatch")
            if p.business_id:
                b = db.scalar(
                    select(Business)
                    .where(Business.id == p.business_id)
                    .with_for_update()
                )
                fund(db, b, p.credits, "payment.funding", p.id, "payment:" + p.id)
            else:
                credit(db, p.user_id, p.credits, "purchase", p.id, "payment:" + p.id)
            p.status = "paid"
        from .payment_settlement import settle
        settle(db, p.user_id)
    elif e.type == 'charge.refunded' or e.type in ('charge.dispute.created', 'charge.dispute.updated', 'charge.dispute.closed'):
        intent = obj.get('payment_intent')
        p = db.scalar(select(Payment).where(Payment.intent_id == intent)) if isinstance(intent, str) else None
        # New checkouts carry our payment ID onto the PaymentIntent/Charge. A refund
        # can arrive before Checkout completion; never credit from this metadata alone.
        if not p and e.type == 'charge.refunded':
            p = db.get(Payment, obj.get('metadata', {}).get('payment_id', ''))
        if not p:
            raise HTTPException(409, 'Payment mapping is not available yet; retry after checkout confirmation')
        if p.business_id:
            raise HTTPException(409, 'Merchant funding reversal requires reconciliation before acknowledgement')
        db.scalar(select(User.id).where(User.id == p.user_id).with_for_update())
        p = db.scalar(select(Payment).where(Payment.id == p.id).with_for_update().execution_options(populate_existing=True))
        if not isinstance(intent, str) or (p.intent_id and p.intent_id != intent):
            raise HTTPException(400, 'Payment intent mismatch')
        if obj.get('currency') != 'gbp':
            raise HTTPException(400, 'Payment currency mismatch')
        p.intent_id = intent
        if e.type == 'charge.refunded':
            amount = obj.get('amount_refunded')
            if type(amount) is not int or not 0 <= amount <= p.amount_pence or obj.get('amount') != p.amount_pence:
                raise HTTPException(400, 'Refund amount mismatch')
            p.refunded_pence = max(p.refunded_pence, amount)
        else:
            status, amount, created = obj.get('status'), obj.get('amount'), envelope.get('created', 0)
            if status not in ('warning_needs_response', 'warning_under_review', 'warning_closed', 'needs_response', 'under_review', 'won', 'lost') or type(amount) is not int or not 0 < amount <= p.amount_pence:
                raise HTTPException(400, 'Dispute details mismatch')
            # Terminal state cannot be reopened by an older delivery, including events
            # created within the same second. Signed event IDs remain deduplicated above.
            if p.dispute_status not in ('won', 'lost', 'warning_closed') and created >= p.dispute_updated:
                p.dispute_status, p.dispute_pence, p.dispute_updated = status, amount, created
        from .payment_settlement import settle
        settle(db, p.user_id)
    db.flush()
    return {"received": True}


class SignageInput(BaseModel):
    category: str = Field(default='General Store', pattern=r'^(Cafe|Restaurant|Retail|Salon|Gym|Entertainment|Professional Services|General Store)$')
    colour: str = Field(default='#245b62', pattern=r'^#[0-9a-fA-F]{6}$')
    logo_url: str = Field(default='', max_length=1500)
    frontage_width: float = Field(default=6, ge=3, le=14, allow_inf_nan=False)
    orientation: float = Field(default=0, ge=-180, le=180, allow_inf_nan=False)
    opening_hours: str = Field(default='', max_length=300)

@router.put('/businesses/{business_id}/signage')
def update_signage(business_id: str, data: SignageInput, user=Depends(current_user), db=Depends(get_db)):
    from urllib.parse import urlparse
    if data.logo_url:
        url=urlparse(data.logo_url)
        if url.scheme!='https' or not url.hostname or url.username or url.password:
            raise HTTPException(422,'Use a public HTTPS logo URL')
    b=tenant(db,business_id,user,lock=True)
    b.signage=data.model_dump()
    audit(db,user,'business.signage_updated',b.id)
    return public_business(b)

def world_businesses(db, city, x, z):
    from .geography import district
    geo=district(city); origin=geo['origin']; result=[]
    lon_scale=111320*math.cos(math.radians(origin['lat']))
    latitude=origin['lat']-z/111320; longitude=origin['lon']+x/lon_scale
    for b in db.scalars(select(Business).where(Business.city==city,Business.status=='verified',Business.latitude.between(latitude-200/111320,latitude+200/111320),Business.longitude.between(longitude-200/lon_scale,longitude+200/lon_scale)).limit(200)):
        bx=(b.longitude-origin['lon'])*111320*math.cos(math.radians(origin['lat']))
        bz=-(b.latitude-origin['lat'])*111320
        if math.hypot(bx-x,bz-z)>200:continue
        campaigns=list(db.scalars(select(Campaign).where(Campaign.business_id==b.id,Campaign.status=='active',Campaign.kind=='visit')))
        rewards=[c.reward_credits for c in campaigns if c.budget_credits-c.spent_credits>=c.reward_credits]
        offers=db.scalar(select(func.count()).select_from(Offer).where(Offer.business_id==b.id,Offer.active==1))
        result.append({**public_business(b),'x':bx,'z':bz,'offer_count':offers,'visit_reward':max(rewards,default=0),'campaigns':[{'id':c.id,'kind':c.kind,'reward_credits':c.reward_credits} for c in campaigns]})
    return result
