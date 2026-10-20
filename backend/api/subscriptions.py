"""Stripe recurring billing. Only signed paid invoices grant time or Credits."""

import hashlib
import json
import math
import os
import time
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    event,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import current_user, require_admin
from .commerce import tenant, fund, Business
from .db import Base, get_db
from .economy import config, credit
from .models import Audit, Config, Entitlement, User

router = APIRouter(prefix="/api", tags=["subscriptions"])


class CustomerSubscription(Base):
    __tablename__ = "customer_subscriptions"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=True)
    plan_id = Column(String, nullable=False)
    plan = Column(JSON, nullable=False)
    request_key = Column(String, nullable=False, unique=True)
    checkout_id = Column(String, unique=True)
    checkout_url = Column(Text)
    provider_id = Column(String, unique=True)
    customer_id = Column(String)
    status = Column(String, nullable=False, default="pending")
    paid_through = Column(Float, nullable=False, default=0)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    terminal_at = Column(Float)
    last_event_at = Column(Float, nullable=False, default=0)
    created_at = Column(Float, default=time.time)


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"
    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False)
    created_at = Column(Float, default=time.time)


class SubscriptionInvoice(Base):
    __tablename__ = "subscription_invoices"
    id = Column(String, primary_key=True)
    subscription_id = Column(
        String, ForeignKey("customer_subscriptions.id"), nullable=False
    )
    period_end = Column(Float, nullable=False)
    credits = Column(Integer, nullable=False)
    created_at = Column(Float, default=time.time)


def immutable(*args):
    raise ValueError("Billing records are immutable")


for model in (SubscriptionEvent, SubscriptionInvoice):
    event.listen(model, "before_update", immutable)
    event.listen(model, "before_delete", immutable)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Plan(Strict):
    id: str = Field(pattern=r"^[a-z0-9_]{3,50}$")
    name: str = Field(min_length=2, max_length=100)
    audience: Literal["consumer", "business"]
    stripe_price_id: str = Field(pattern=r"^price_[A-Za-z0-9]+$")
    amount_pence: int = Field(gt=0, le=10000000, strict=True)
    currency: Literal["gbp"] = "gbp"
    interval: Literal["month", "year"]
    credits: int = Field(default=0, ge=0, le=1000000, strict=True)
    features: list[str] = Field(default_factory=list, max_length=20)


class Catalog(Strict):
    plans: list[Plan] = Field(max_length=30)


def catalog(db):
    try:
        result = Catalog.model_validate(
            config(db, "subscription_catalog", {"plans": []})
        )
        if len({p.id for p in result.plans}) != len(result.plans):
            raise ValueError("Duplicate plan")
        return result
    except (ValidationError, ValueError):
        raise HTTPException(
            503, "Subscription catalog is invalid; administrator action required"
        )


@router.get("/subscriptions/plans")
def plans(db: Session = Depends(get_db)):
    rows = catalog(db).plans
    return {
        "configured": bool(rows) and bool(os.getenv("STRIPE_SECRET_KEY")),
        "plans": [p.model_dump(exclude={"stripe_price_id"}) for p in rows],
    }


@router.get("/admin/subscriptions/plans")
def admin_plans(u=Depends(require_admin), db: Session = Depends(get_db)):
    return catalog(db).model_dump()


@router.put("/admin/subscriptions/plans")
def save_plans(data: Catalog, u=Depends(require_admin), db: Session = Depends(get_db)):
    if len({p.id for p in data.plans}) != len(data.plans):
        raise HTTPException(422, "Plan IDs must be unique")
    row = db.get(Config, "subscription_catalog")
    if row:
        row.value = data.model_dump()
        row.updated_at = time.time()
    else:
        db.add(Config(key="subscription_catalog", value=data.model_dump()))
    db.add(
        Audit(
            actor_id=u.id,
            action="subscription.catalog.update",
            target="subscription_catalog",
            details=data.model_dump(),
        )
    )
    return data.model_dump()


def secret():
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise HTTPException(503, "Subscriptions unavailable: Stripe is not configured")
    return key


def origin():
    url = os.getenv("PUBLIC_APP_URL", "").rstrip("/")
    if not url.startswith(("https://", "http://localhost:")):
        raise HTTPException(503, "Public application URL is not configured")
    return url


class Subscribe(Strict):
    plan_id: str
    business_id: str | None = None
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), min_length=8, max_length=100
    )


@router.post("/subscriptions/checkout")
def checkout(data: Subscribe, u=Depends(current_user), db: Session = Depends(get_db)):
    import stripe

    key = secret()
    base = origin()
    plan = next((p for p in catalog(db).plans if p.id == data.plan_id), None)
    if not plan:
        raise HTTPException(
            503 if not catalog(db).plans else 422, "Subscription plan unavailable"
        )
    if plan.audience == "business":
        b = tenant(db, data.business_id, u)
        if b.status != "verified":
            raise HTTPException(409, "Business verification required")
    elif data.business_id:
        raise HTTPException(422, "Consumer plans cannot be assigned to businesses")
    db.scalar(select(User).where(User.id == u.id).with_for_update())
    request_key = u.id + ":" + data.request_id
    previous = db.scalar(
        select(CustomerSubscription).where(
            CustomerSubscription.request_key == request_key
        )
    )
    if previous:
        if previous.plan_id != plan.id or previous.business_id != data.business_id:
            raise HTTPException(409, "Request ID already used for another subscription")
        return {"url": previous.checkout_url, "subscription_id": previous.id}
    existing = db.scalar(
        select(CustomerSubscription).where(
            CustomerSubscription.user_id == u.id,
            CustomerSubscription.business_id == data.business_id,
            CustomerSubscription.status.notin_(
                ["canceled", "expired", "incomplete_expired"]
            ),
        )
    )
    if existing:
        raise HTTPException(
            409,
            "An existing subscription or checkout must be managed before starting another",
        )
    row = CustomerSubscription(
        id=str(uuid.uuid5(uuid.NAMESPACE_URL, "pulse-subscription:" + request_key)),
        user_id=u.id,
        business_id=data.business_id,
        plan_id=plan.id,
        plan=plan.model_dump(),
        request_key=request_key,
    )
    db.add(row)
    db.flush()
    try:
        # Validate the provider price before charging; admin text cannot misstate checkout pricing.
        price = stripe.Price.retrieve(plan.stripe_price_id, api_key=key)
        if (
            not price.get("active")
            or price.get("unit_amount") != plan.amount_pence
            or price.get("currency") != plan.currency
            or price.get("recurring", {}).get("interval") != plan.interval
            or price.get("recurring", {}).get("interval_count") != 1
        ):
            raise HTTPException(
                503, "Configured subscription price does not match Stripe"
            )
        session = stripe.checkout.Session.create(
            api_key=key,
            idempotency_key="pulse-sub:"
            + hashlib.sha256(request_key.encode()).hexdigest(),
            mode="subscription",
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            metadata={"pulse_subscription_id": row.id},
            subscription_data={"metadata": {"pulse_subscription_id": row.id}},
            success_url=base + "/wallet?subscription=returned",
            cancel_url=base + "/wallet?subscription=cancelled",
        )
    except stripe.StripeError:
        raise HTTPException(
            502, "Billing provider unavailable; retry with the same request ID"
        )
    row.checkout_id = session.id
    row.checkout_url = session.url
    db.add(
        Audit(
            actor_id=u.id,
            action="subscription.checkout",
            target=row.id,
            details={"plan": plan.id},
        )
    )
    return {"url": session.url, "subscription_id": row.id}


def effective_end(row):
    return (
        min(row.paid_through, row.terminal_at) if row.terminal_at else row.paid_through
    )


@router.get("/subscriptions")
def status(u=Depends(current_user), db: Session = Depends(get_db)):
    return [
        {
            "id": r.id,
            "plan_id": r.plan_id,
            "business_id": r.business_id,
            "status": r.status,
            "active": effective_end(r) > time.time(),
            "paid_through": effective_end(r),
            "cancel_at_period_end": r.cancel_at_period_end,
        }
        for r in db.scalars(
            select(CustomerSubscription).where(CustomerSubscription.user_id == u.id)
        )
    ]


@router.post("/subscriptions/{subscription_id}/portal")
def portal(
    subscription_id: str, u=Depends(current_user), db: Session = Depends(get_db)
):
    import stripe

    row = db.scalar(
        select(CustomerSubscription).where(
            CustomerSubscription.id == subscription_id,
            CustomerSubscription.user_id == u.id,
        )
    )
    if not row:
        raise HTTPException(404, "Subscription not found")
    if not row.customer_id:
        raise HTTPException(
            409, "Checkout has not yet been confirmed by the billing provider"
        )
    try:
        session = stripe.billing_portal.Session.create(
            api_key=secret(), customer=row.customer_id, return_url=origin() + "/wallet"
        )
    except stripe.StripeError:
        raise HTTPException(502, "Billing portal unavailable")
    return {"url": session.url}


def refresh_entitlement(db, row):
    if row.business_id:
        return
    db.scalar(select(User).where(User.id == row.user_id).with_for_update())
    db.flush()
    until = max(
        (
            effective_end(r)
            for r in db.scalars(
                select(CustomerSubscription).where(
                    CustomerSubscription.user_id == row.user_id,
                    CustomerSubscription.business_id.is_(None),
                )
            )
        ),
        default=0,
    )
    entitlement = db.get(Entitlement, (row.user_id, "pulse_plus"))
    if entitlement:
        entitlement.expires_at = until
    elif until > time.time():
        db.add(Entitlement(user_id=row.user_id, kind="pulse_plus", expires_at=until))


def apply_event(db, kind, obj, created):
    if kind.startswith("checkout.session."):
        if obj.get("mode") != "subscription":
            return
        row = db.scalar(
            select(CustomerSubscription)
            .where(CustomerSubscription.checkout_id == obj["id"])
            .with_for_update()
        )
        if not row:
            raise HTTPException(409, "Subscription checkout not persisted yet; retry")
        if obj.get("metadata", {}).get("pulse_subscription_id") != row.id:
            raise HTTPException(400, "Subscription metadata mismatch")
        if kind == "checkout.session.expired" and row.status == "pending":
            row.status = "expired"
        if kind == "checkout.session.completed":
            row.provider_id = obj.get("subscription")
            row.customer_id = obj.get("customer")
        return  # Browser/checkout success NEVER grants entitlements.
    if kind not in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.paid",
        "invoice.payment_failed",
    ):
        return
    is_invoice = kind.startswith("invoice.")
    details = (
        obj.get("parent", {}).get("subscription_details", {})
        or obj.get("subscription_details", {})
        or {}
    )
    provider_id = (
        (obj.get("subscription") or details.get("subscription"))
        if is_invoice
        else obj["id"]
    )
    local_id = (
        details.get("metadata", {}) if is_invoice else obj.get("metadata", {})
    ).get("pulse_subscription_id")
    row = (
        db.scalar(
            select(CustomerSubscription)
            .where(CustomerSubscription.provider_id == provider_id)
            .with_for_update()
        )
        if provider_id
        else None
    )
    if not row and local_id:
        row = db.scalar(
            select(CustomerSubscription)
            .where(CustomerSubscription.id == local_id)
            .with_for_update()
        )
    if not row:
        if local_id:
            raise HTTPException(409, "Subscription record not persisted yet; retry")
        return  # Unrelated Stripe products use the same account.
    if (
        not provider_id
        or (row.provider_id and row.provider_id != provider_id)
        or (local_id and local_id != row.id)
    ):
        raise HTTPException(400, "Subscription identity mismatch")
    row.provider_id = provider_id
    if row.customer_id and obj.get("customer") != row.customer_id:
        raise HTTPException(400, "Subscription customer mismatch")
    row.customer_id = obj.get("customer") or row.customer_id
    if is_invoice:
        if kind == "invoice.payment_failed":
            if created > row.last_event_at and not row.terminal_at:
                row.status = "past_due"
                row.last_event_at = created
            return
        if obj.get("status") != "paid" or obj.get("currency") != row.plan["currency"]:
            raise HTTPException(400, "Invoice is not paid in the configured currency")
        if db.get(SubscriptionInvoice, obj["id"]):
            return
        lines = obj.get("lines", {}).get("data", [])
        matching = [
            line
            for line in lines
            if (
                line.get("price", {}).get("id")
                or line.get("pricing", {}).get("price_details", {}).get("price")
            )
            == row.plan["stripe_price_id"]
            and not line.get("proration", False)
            and not line.get("parent", {})
            .get("subscription_item_details", {})
            .get("proration", False)
        ]
        if len(matching) != 1 or obj.get("billing_reason") not in (
            "subscription_create",
            "subscription_cycle",
        ):
            raise HTTPException(
                400,
                "Unsupported invoice billing structure; manual billing review required",
            )
        line = matching[0]
        end = line.get("period", {}).get("end", 0)
        start = line.get("period", {}).get("start", 0)
        if (
            any(
                type(value) not in (int, float) or not math.isfinite(value)
                for value in (start, end)
            )
            or start < 0
            or end <= start
            or line.get("quantity", 1) != 1
        ):
            raise HTTPException(400, "Invalid subscription billing period")
        # Only the configured full-price renewal funds Credits. Discounted, manually
        # marked-paid, or partial invoices require billing review rather than minting.
        if (
            line.get("amount") != row.plan["amount_pence"]
            or type(obj.get("amount_paid")) is not int
            or obj["amount_paid"] < row.plan["amount_pence"]
            or obj.get("amount_remaining") != 0
            or obj.get("paid_out_of_band", False)
        ):
            raise HTTPException(
                400,
                "Invoice payment does not match the configured plan; manual billing review required",
            )
        db.add(
            SubscriptionInvoice(
                id=obj["id"],
                subscription_id=row.id,
                period_end=end,
                credits=row.plan["credits"],
            )
        )
        db.flush()
        row.paid_through = max(row.paid_through, end)
        if created >= row.last_event_at and not row.terminal_at:
            row.status = "active"
            row.last_event_at = created
        if row.plan["credits"]:
            if row.business_id:
                b = db.scalar(
                    select(Business)
                    .where(Business.id == row.business_id)
                    .with_for_update()
                )
                fund(
                    db,
                    b,
                    row.plan["credits"],
                    "subscription",
                    obj["id"],
                    "subscription:" + obj["id"],
                )
            else:
                credit(
                    db,
                    row.user_id,
                    row.plan["credits"],
                    "subscription",
                    obj["id"],
                    "subscription:" + obj["id"],
                )
    elif created >= row.last_event_at:
        row.last_event_at = created
        row.status = obj.get(
            "status", "canceled" if kind.endswith("deleted") else "incomplete"
        )
        row.cancel_at_period_end = bool(obj.get("cancel_at_period_end", False))
        if kind.endswith("deleted") or row.status in ("canceled", "incomplete_expired"):
            row.terminal_at = obj.get("ended_at") or created
    refresh_entitlement(db, row)


@router.post("/subscriptions/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    import stripe

    signing = os.getenv("STRIPE_SUBSCRIPTION_WEBHOOK_SECRET")
    if not signing:
        raise HTTPException(
            503, "Subscription webhook signing secret is not configured"
        )
    payload = await request.body()
    if len(payload) > 262144:
        raise HTTPException(413, "Webhook too large")
    try:
        event_data = stripe.Webhook.construct_event(
            payload, request.headers.get("stripe-signature", ""), signing, tolerance=300
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, "Invalid webhook signature")
    if db.get(SubscriptionEvent, event_data.id):
        return {"received": True, "duplicate": True}
    try:
        with db.begin_nested():
            db.add(SubscriptionEvent(id=event_data.id, event_type=event_data.type))
            db.flush()
    except IntegrityError:
        return {"received": True, "duplicate": True}
    data = json.loads(payload)
    apply_event(db, event_data.type, data["data"]["object"], data.get("created", 0))
    db.flush()
    return {"received": True}
