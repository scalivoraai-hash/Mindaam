import time
import uuid
from sqlalchemy import (
    Index, func,
    String,
    Integer,
    Float,
    Boolean,
    JSON,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def uid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(30), default="consumer")
    city: Mapped[str] = mapped_column(String(50), default="london")
    privacy: Mapped[str] = mapped_column(String(30), default="City Mode")
    avatar: Mapped[dict] = mapped_column(JSON, default=dict)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    interests: Mapped[list] = mapped_column(JSON, default=list)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    location_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    analytics_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


Index('uq_users_username_normalized', func.lower(func.trim(User.username)), unique=True)

class Session(Base):
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[float] = mapped_column(Float)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Consent(Base):
    __tablename__ = "user_consents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    document: Mapped[str] = mapped_column(String(40))
    version: Mapped[str] = mapped_column(String(30), default="draft-1")
    accepted: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Config(Base):
    __tablename__ = "configuration_versions"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)


class Ledger(Base):
    __tablename__ = "wallet_transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    currency: Mapped[str] = mapped_column(String(20))
    amount: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(60))
    source: Mapped[str] = mapped_column(String(100))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    previous_balance: Mapped[int] = mapped_column(Integer)
    balance: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    __table_args__ = (
        UniqueConstraint("user_id", "currency", "idempotency_key"),
        CheckConstraint("currency IN ('credits','xp')"),
        CheckConstraint("balance >= 0"),
    )


class Presence(Base):
    __tablename__ = "user_presence"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    city: Mapped[str] = mapped_column(String(50), index=True)
    x: Mapped[float] = mapped_column(Float, default=0)
    z: Mapped[float] = mapped_column(Float, default=0)
    return_position: Mapped[dict] = mapped_column(JSON, default=dict)
    zone_id: Mapped[str] = mapped_column(String(100), default="world", index=True)
    mode: Mapped[str] = mapped_column(String(20), default="walk")
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)
    last_move: Mapped[float] = mapped_column(Float, default=time.time)
    motion_speed: Mapped[float] = mapped_column(Float, default=0, server_default="0")


class Collectible(Base):
    __tablename__ = "collectible_instances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    city: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(20))
    x: Mapped[float] = mapped_column(Float)
    z: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[float] = mapped_column(Float, default=0)
    ends_at: Mapped[float] = mapped_column(Float, default=4102444800)
    origin: Mapped[str] = mapped_column(String(16), default="authored", server_default="authored")
    max_claims: Mapped[int] = mapped_column(Integer, default=100000)
    claims: Mapped[int] = mapped_column(Integer, default=0)


class Claim(Base):
    __tablename__ = "collectible_claims"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    collectible_id: Mapped[str] = mapped_column(ForeignKey("collectible_instances.id"))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    __table_args__ = (UniqueConstraint("user_id", "collectible_id"),)


class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(500))
    city: Mapped[str] = mapped_column(String(50))
    requirements: Mapped[dict] = mapped_column(JSON)
    credits: Mapped[int] = mapped_column(Integer)
    xp: Mapped[int] = mapped_column(Integer)


class MissionCompletion(Base):
    __tablename__ = "mission_progress"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id"))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    __table_args__ = (UniqueConstraint("user_id", "mission_id"),)


class Social(Base):
    __tablename__ = "social_relationships"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    target: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    __table_args__ = (UniqueConstraint("actor", "target", "kind"),)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    sender: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    recipient: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(String(2000))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Crew(Base):
    __tablename__ = "crews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    city: Mapped[str] = mapped_column(String(50))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    private: Mapped[bool] = mapped_column(Boolean, default=False)


class CrewMember(Base):
    __tablename__ = "crew_members"
    crew_id: Mapped[str] = mapped_column(ForeignKey("crews.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="member")


class Event(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    host_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(1000), default="")
    city: Mapped[str] = mapped_column(String(50))
    starts_at: Mapped[float] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer, default=100)
    venue_experience_type: Mapped[str] = mapped_column(String(30), default="standard")
    venue_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    chat_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    event_type: Mapped[str] = mapped_column(String(30), default='Social Hangout')
    communication_mode: Mapped[str] = mapped_column(String(20), default='text')
    visibility: Mapped[str] = mapped_column(String(20), default='public')
    status: Mapped[str] = mapped_column(String(20), default='scheduled')
    ends_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    zone_id: Mapped[str] = mapped_column(String(80), default='')
    x: Mapped[float | None] = mapped_column(Float, nullable=True)
    z: Mapped[float | None] = mapped_column(Float, nullable=True)
    reminded: Mapped[bool] = mapped_column(Boolean, default=False)
    presentation: Mapped[dict] = mapped_column(JSON, default=dict, server_default='{}')
    lighting: Mapped[dict] = mapped_column(JSON, default=dict, server_default='{}')
    ticket_price: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    programme: Mapped[dict] = mapped_column(JSON, default=dict, server_default='{}')


class Attendee(Base):
    __tablename__ = "event_attendees"
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    state: Mapped[str] = mapped_column(String(20), default='active')
    role: Mapped[str] = mapped_column(String(20), default='audience')
    joined_at: Mapped[float] = mapped_column(Float, default=time.time)
    permission_dirty: Mapped[bool] = mapped_column(Boolean, default=False)
    permission_revision: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    share_state: Mapped[str] = mapped_column(String(20), default='none', server_default='none')
    hand: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[float] = mapped_column(Float, default=time.time)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    body: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Audit(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Analytics(Base):
    __tablename__ = "analytics_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    reporter_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    target_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String(40))
    details: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class MediaSession(Base):
    __tablename__ = "media_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    requester: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    target: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(20), default="pending")
    event_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    max_participants: Mapped[int] = mapped_column(Integer, default=6)
    distance_policy: Mapped[str] = mapped_column(String(20), default="proximity")
    join_policy: Mapped[str] = mapped_column(String(30), default="approval")
    end_reason: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    accepted_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    ended_at: Mapped[float | None] = mapped_column(Float, nullable=True)


class ConversationMember(Base):
    __tablename__ = 'conversation_members'
    session_id: Mapped[str] = mapped_column(ForeignKey('media_sessions.id'), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    state: Mapped[str] = mapped_column(String(20), default='active')
    joined_at: Mapped[float] = mapped_column(Float, default=time.time)
    left_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    rejoin_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="JOINED_PARTICIPANT")
    out_since: Mapped[float | None] = mapped_column(Float, nullable=True)
    warning: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str | None] = mapped_column(String(60), nullable=True)

class ConversationJoin(Base):
    __tablename__ = 'conversation_join_requests'
    session_id: Mapped[str] = mapped_column(ForeignKey('media_sessions.id'), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    state: Mapped[str] = mapped_column(String(20), default='pending')
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    decided_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)



class Referral(Base):
    __tablename__ = "referrals"
    referred_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    referrer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    rewarded: Mapped[bool] = mapped_column(Boolean, default=False)


class Entitlement(Base):
    __tablename__ = "subscription_entitlements"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(50), primary_key=True)
    expires_at: Mapped[float] = mapped_column(Float, default=4102444800)
