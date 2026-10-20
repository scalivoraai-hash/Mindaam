"""Single-use identity links and transactional email outbox."""

import hashlib
import json
import os
import secrets
import smtplib
import ssl
import time
import uuid
from email.message import EmailMessage
from pathlib import Path
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, delete, select
from .db import Base, SessionLocal, get_db
from .models import User, Session as AuthSession, Audit
from .auth import hash_password

router = APIRouter(prefix="/api/auth", tags=["identity"])


class IdentityToken(Base):
    __tablename__ = "identity_tokens"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    purpose = Column(String, nullable=False)
    expires_at = Column(Float, nullable=False)
    consumed_at = Column(Float, nullable=True)
    created_at = Column(Float, nullable=False, default=time.time)


class MailOutbox(Base):
    __tablename__ = "mail_outbox"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    encrypted = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="queued")
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt = Column(Float, nullable=False, default=time.time)
    created_at = Column(Float, nullable=False, default=time.time)
    sent_at = Column(Float, nullable=True)


def local():
    return os.getenv("APP_ENV", "local") in {"local", "test"}


def mail_configuration():
    origin = os.getenv("PUBLIC_APP_URL", "http://localhost:3000").rstrip("/")
    if not local():
        if (
            not os.getenv("SMTP_HOST")
            or not os.getenv("SMTP_FROM")
            or not os.getenv("MAIL_ENCRYPTION_KEY")
            or not origin.startswith("https://")
        ):
            raise HTTPException(
                503,
                "Account email is unavailable until secure mail delivery is configured",
            )
    key = os.getenv("MAIL_ENCRYPTION_KEY")
    try:
        cipher = Fernet(key.encode()) if key else None
    except ValueError:
        raise HTTPException(503, "Mail encryption configuration is invalid")
    return origin, cipher


def send_token(db, email, purpose):
    """Queue delivery in caller transaction; return no raw token, even locally."""
    if purpose not in {"verify", "reset"}:
        raise ValueError("Invalid token purpose")
    origin, cipher = mail_configuration()
    user = db.scalar(
        select(User)
        .where(User.email == email.strip().lower(), User.suspended == False)
        .with_for_update()
    )
    if not user or (purpose == "verify" and user.verified):
        return
    recent = db.scalar(
        select(IdentityToken)
        .where(IdentityToken.user_id == user.id, IdentityToken.purpose == purpose)
        .order_by(IdentityToken.created_at.desc())
    )
    if recent and recent.created_at > time.time() - 60:
        return
    for row in db.scalars(
        select(IdentityToken).where(
            IdentityToken.user_id == user.id,
            IdentityToken.purpose == purpose,
            IdentityToken.consumed_at == None,
        )
    ):
        row.consumed_at = time.time()
    token = secrets.token_urlsafe(40)
    db.add(
        IdentityToken(
            id=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            purpose=purpose,
            expires_at=time.time() + (3600 if purpose == "verify" else 900),
        )
    )
    path = "verify-email" if purpose == "verify" else "reset-password"
    payload = json.dumps(
        {
            "to": user.email,
            "subject": "Verify your MyLilWorlds email"
            if purpose == "verify"
            else "Reset your MyLilWorlds password",
            "body": f"Open this one-time link: {origin}/{path}#token={token}\n\nIf you did not request this, ignore this message. The link expires in "
            + ("60 minutes." if purpose == "verify" else "15 minutes."),
        }
    )
    db.add(
        MailOutbox(
            user_id=user.id,
            payload=cipher.encrypt(payload.encode()).decode() if cipher else payload,
            encrypted=int(cipher is not None),
        )
    )
    db.add(
        Audit(
            actor_id=user.id,
            action="identity.email_queued",
            target=user.id,
            details={"purpose": purpose},
        )
    )
    db.flush()


class EmailInput(BaseModel):
    email: str = Field(
        min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )


@router.post("/request-verification", status_code=202)
def request_verification(data: EmailInput, db=Depends(get_db)):
    send_token(db, data.email, "verify")
    return {
        "accepted": True,
        "message": "If the account is eligible, an email will be sent.",
    }


@router.post("/forgot-password", status_code=202)
def forgot(data: EmailInput, db=Depends(get_db)):
    send_token(db, data.email, "reset")
    return {
        "accepted": True,
        "message": "If the account is eligible, an email will be sent.",
    }


class TokenInput(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class ResetInput(TokenInput):
    password: str = Field(min_length=12, max_length=128)


def consume(db, raw, purpose):
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    initial = db.get(IdentityToken, hashed)
    if not initial:
        raise HTTPException(400, "Invalid or expired identity link")
    u = db.scalar(select(User).where(User.id == initial.user_id).with_for_update())
    t = db.scalar(
        select(IdentityToken)
        .where(IdentityToken.id == hashed)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        not u
        or u.suspended
        or not t
        or t.purpose != purpose
        or t.consumed_at
        or t.expires_at < time.time()
    ):
        raise HTTPException(400, "Invalid or expired identity link")
    t.consumed_at = time.time()
    return u


@router.post("/verify-email")
def verify(data: TokenInput, db=Depends(get_db)):
    u = consume(db, data.token, "verify")
    u.verified = True
    db.add(Audit(actor_id=u.id, action="identity.email_verified", target=u.id))
    return {"verified": True}


@router.post("/reset-password")
def reset(data: ResetInput, db=Depends(get_db)):
    u = consume(db, data.token, "reset")
    u.must_change_password=False
    u.password_hash = hash_password(data.password)
    db.execute(delete(AuthSession).where(AuthSession.user_id == u.id))
    for token in db.scalars(
        select(IdentityToken).where(
            IdentityToken.user_id == u.id, IdentityToken.consumed_at == None
        )
    ):
        token.consumed_at = time.time()
    db.add(Audit(actor_id=u.id, action="identity.password_reset", target=u.id))
    return {
        "reset": True,
        "message": "Password updated. Sign in again on every device.",
    }


def drain_outbox(limit=20):
    """Worker invoked after request commit. Delivery is at least once across crashes."""
    _, cipher = mail_configuration()
    sent = failed = 0
    for _ in range(min(max(limit, 1), 100)):
        with SessionLocal.begin() as db:
            row = db.scalar(
                select(MailOutbox)
                .where(
                    MailOutbox.status == "queued",
                    MailOutbox.next_attempt <= time.time(),
                    MailOutbox.attempts < 5,
                )
                .order_by(MailOutbox.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if not row:
                break
            row.attempts += 1
            try:
                payload = json.loads(
                    cipher.decrypt(row.payload.encode()).decode()
                    if row.encrypted and cipher
                    else row.payload
                )
                msg = EmailMessage()
                msg["To"] = payload["to"]
                msg["From"] = os.getenv("SMTP_FROM", "noreply@pulseworld.local")
                msg["Subject"] = payload["subject"]
                msg["Message-ID"] = f"<{row.id}@pulseworld>"
                msg.set_content(payload["body"])
                host = os.getenv("SMTP_HOST")
                if host:
                    with smtplib.SMTP(
                        host, int(os.getenv("SMTP_PORT", "587")), timeout=15
                    ) as server:
                        server.starttls(context=ssl.create_default_context())
                        if os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME"):
                            server.login(
                                os.getenv("SMTP_USER") or os.environ["SMTP_USERNAME"],
                                os.environ.get("SMTP_PASSWORD", ""),
                            )
                        server.send_message(msg)
                elif local():
                    path = Path(os.getenv("LOCAL_MAIL_DIR", "./local-mail-outbox"))
                    path.mkdir(parents=True, exist_ok=True, mode=0o700)
                    output = path / (row.id + ".eml")
                    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                    with os.fdopen(fd, "w") as f:
                        f.write(msg.as_string())
                else:
                    raise RuntimeError("SMTP not configured")
                row.status = "sent"
                row.sent_at = time.time()
                row.payload = ""
                sent += 1
            except Exception:
                row.next_attempt = time.time() + 60 * (2**row.attempts)
                if row.attempts >= 5:
                    row.status = "failed"
                    row.payload = ""
                failed += 1
    return {"sent": sent, "failed": failed}


def commerce_export(db, user):
    from .commerce import (
        Business,
        Product,
        Offer,
        Campaign,
        FundingLedger,
        Visit,
        Perk,
        Payment,
        StoreVisit,
        CommerceAudit,
        record,
    )

    owned = list(db.scalars(select(Business.id).where(Business.owner_id == user.id)))
    result = {}
    for name, model, condition in [
        ("businesses", Business, Business.owner_id == user.id),
        ("products", Product, Product.business_id.in_(owned)),
        ("offers", Offer, Offer.business_id.in_(owned)),
        ("campaigns", Campaign, Campaign.business_id.in_(owned)),
        ("funding_ledger", FundingLedger, FundingLedger.business_id.in_(owned)),
        ("visits", Visit, Visit.user_id == user.id),
        ("virtual_visits", StoreVisit, StoreVisit.user_id == user.id),
        ("perks", Perk, Perk.user_id == user.id),
        ("payments", Payment, Payment.user_id == user.id),
        ("commerce_audit", CommerceAudit, CommerceAudit.actor_id == user.id),
    ]:
        result[name] = [record(x) for x in db.scalars(select(model).where(condition))]
    for p in result["payments"]:
        p.pop("checkout_url", None)
    return result


def anonymise_commerce(db, user):
    """Hide merchant listings, release reservations, revoke links; retain accounting."""
    from .commerce import Business, Campaign, Product, Offer, PulsePoint, fund

    for t in db.scalars(select(IdentityToken).where(IdentityToken.user_id == user.id)):
        t.consumed_at = time.time()
    for mail in db.scalars(select(MailOutbox).where(MailOutbox.user_id == user.id)):
        mail.payload = ""
        mail.status = "cancelled"
    for p in db.scalars(select(PulsePoint).where(PulsePoint.user_id == user.id)):
        p.consumed_at = time.time()
    owned = list(db.scalars(select(Business.id).where(Business.owner_id == user.id)))
    list(
        db.scalars(
            select(Campaign)
            .where(Campaign.business_id.in_(owned))
            .order_by(Campaign.id)
            .with_for_update()
        )
    )
    businesses = list(
        db.scalars(
            select(Business).where(Business.owner_id == user.id).with_for_update()
        )
    )
    for b in businesses:
        for camp in db.scalars(
            select(Campaign).where(Campaign.business_id == b.id).with_for_update()
        ):
            if camp.status == "active":
                fund(
                    db,
                    b,
                    camp.budget_credits - camp.spent_credits,
                    "campaign.release",
                    camp.id,
                    "release:" + camp.id,
                )
            camp.status = "closed"
            camp.title = "Closed campaign"
        b.status = "closed"
        b.name = "Closed business"
        b.description = ""
        b.address = ""
        b.latitude = 0
        b.longitude = 0
        for p in db.scalars(select(Product).where(Product.business_id == b.id)):
            p.name = "Unavailable"
            p.description = ""
        for o in db.scalars(select(Offer).where(Offer.business_id == b.id)):
            o.active = 0
            o.title = "Unavailable"
            o.description = ""
