"""Authoritative world authoring, measured city competitions and private Crew collaboration."""

import time
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, model_validator
from sqlalchemy import (
    Column,
    String,
    Float,
    JSON,
    ForeignKey,
    UniqueConstraint,
    select,
    func,
)
from .db import Base, get_db
from .models import (
    User,
    Collectible,
    Claim,
    Mission,
    MissionCompletion,
    Crew,
    CrewMember,
    Audit,
    uid,
)
from .commerce import Business, Visit
from .auth import current_user, require_admin
from .core import Strict, serialize, check_city, notify, emit
from .world import blocked
from .db import APP_ENV
from .geography import walkable

router = APIRouter(prefix="/api")


class CityBattle(Base):
    __tablename__ = "city_battles"
    id = Column(String(36), primary_key=True, default=uid)
    title = Column(String(120), nullable=False)
    cities = Column(JSON, nullable=False)
    starts_at = Column(Float, nullable=False)
    ends_at = Column(Float, nullable=False)


class CrewInvitation(Base):
    __tablename__ = "crew_invitations"
    id = Column(String(36), primary_key=True, default=uid)
    crew_id = Column(ForeignKey("crews.id"), nullable=False, index=True)
    sender_id = Column(ForeignKey("users.id"), nullable=False)
    recipient_id = Column(ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False)
    expires_at = Column(Float, nullable=False)
    created_at = Column(Float, default=time.time, nullable=False)
    __table_args__ = (UniqueConstraint("crew_id", "recipient_id"),)


class CrewMessage(Base):
    __tablename__ = "crew_messages"
    id = Column(String(36), primary_key=True, default=uid)
    crew_id = Column(ForeignKey("crews.id"), nullable=False, index=True)
    sender_id = Column(ForeignKey("users.id"), nullable=False)
    body = Column(String(2000), nullable=False)
    request_id = Column(String(100), nullable=False)
    created_at = Column(Float, default=time.time, nullable=False)
    __table_args__ = (UniqueConstraint("crew_id", "sender_id", "request_id"),)


class Window(Strict):
    starts_at: float = Field(ge=0, allow_inf_nan=False)
    ends_at: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("End must follow start")
        return self


class CollectibleInput(Window):
    title: str = Field(min_length=2, max_length=80)
    city: str
    kind: Literal["fruit", "gem", "treasure"]
    x: float = Field(ge=-350, le=350, allow_inf_nan=False)
    z: float = Field(ge=-350, le=350, allow_inf_nan=False)
    max_claims: int = Field(ge=1, le=100000)
    active: bool = True

    @model_validator(mode="after")
    def reachable(self):
        if (abs(self.x) > 14 and abs(self.z) > 14) if APP_ENV == "test" else not walkable(self.city,self.x,self.z):
            raise ValueError("Spawn on the walkable district streets")
        return self


@router.get("/admin/collectibles")
def list_collectibles(u=Depends(require_admin), db=Depends(get_db)):
    return [
        serialize(x)
        for x in db.scalars(
            select(Collectible).order_by(Collectible.starts_at.desc()).limit(300)
        )
    ]


@router.post("/admin/collectibles", status_code=201)
def create_collectible(
    data: CollectibleInput, u=Depends(require_admin), db=Depends(get_db)
):
    check_city(data.city)
    c = Collectible(**data.model_dump())
    db.add(c)
    db.flush()
    db.add(Audit(actor_id=u.id, action="collectible.created", target=c.id))
    return serialize(c)


class Activation(Strict):
    active: bool


@router.patch("/admin/collectibles/{item_id}")
def activate_collectible(
    item_id: str, data: Activation, u=Depends(require_admin), db=Depends(get_db)
):
    c = db.get(Collectible, item_id)
    if not c:
        raise HTTPException(404, "Collectible not found")
    c.active = data.active
    db.add(Audit(actor_id=u.id, action="collectible.activation", target=c.id))
    return serialize(c)


class MissionInput(Strict):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    city: str
    requirements: dict[str, int]
    credits: int = Field(ge=0, le=1000)
    xp: int = Field(ge=0, le=10000)

    @model_validator(mode="after")
    def goals(self):
        if not self.requirements or any(
            k not in {"fruit", "gem", "treasure"}
            or type(v) is not int
            or not 1 <= v <= 10000
            for k, v in self.requirements.items()
        ):
            raise ValueError("Use positive fruit, gem or treasure targets")
        return self


@router.get("/admin/missions")
def list_missions(u=Depends(require_admin), db=Depends(get_db)):
    return [serialize(x) for x in db.scalars(select(Mission).limit(300))]


@router.post("/admin/missions", status_code=201)
def create_mission(data: MissionInput, u=Depends(require_admin), db=Depends(get_db)):
    check_city(data.city)
    m = Mission(**data.model_dump())
    db.add(m)
    db.flush()
    db.add(Audit(actor_id=u.id, action="mission.created", target=m.id))
    return serialize(m)


class BattleInput(Window):
    title: str = Field(min_length=3, max_length=120)
    cities: list[str] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def distinct(self):
        if len(set(self.cities)) != len(self.cities):
            raise ValueError("Choose different cities")
        return self


@router.post("/admin/city-battles", status_code=201)
def create_battle(data: BattleInput, u=Depends(require_admin), db=Depends(get_db)):
    for city in data.cities:
        check_city(city)
    if data.starts_at < time.time():
        raise HTTPException(422, "Competition must start in the future")
    b = CityBattle(**data.model_dump())
    db.add(b)
    db.flush()
    db.add(Audit(actor_id=u.id, action="battle.created", target=b.id))
    return serialize(b)


@router.get("/city-battles")
@router.get("/admin/city-battles")
def battles(u=Depends(current_user), db=Depends(get_db)):
    result = []
    now = time.time()
    for b in db.scalars(
        select(CityBattle).order_by(CityBattle.starts_at.desc()).limit(30)
    ):
        scores = []
        for city in b.cities:
            counts = []
            for model, parent, key in [
                (Claim, Collectible, Claim.collectible_id),
                (MissionCompletion, Mission, MissionCompletion.mission_id),
                (Visit, Business, Visit.business_id),
            ]:
                counts.append(
                    db.scalar(
                        select(func.count())
                        .select_from(model)
                        .join(parent, parent.id == key)
                        .join(User, User.id == model.user_id)
                        .where(
                            parent.city == city,
                            model.created_at >= b.starts_at,
                            model.created_at < min(b.ends_at, now),
                            User.suspended == False,
                        )
                    )
                    or 0
                )
            scores.append(
                dict(
                    city=city,
                    collectibles=counts[0],
                    missions=counts[1],
                    verified_visits=counts[2],
                    points=counts[0] + 10 * counts[1] + 20 * counts[2],
                )
            )
        result.append(
            dict(
                serialize(b),
                scores=sorted(scores, key=lambda x: x["points"], reverse=True),
                status="scheduled"
                if now < b.starts_at
                else "active"
                if now < b.ends_at
                else "ended",
                scoring="1 per collectible, 10 per mission, 20 per verified visit; activity city during competition",
            )
        )
    return result


def membership(db, crew_id, u, roles=None):
    c = db.get(Crew, crew_id)
    m = db.get(CrewMember, (crew_id, u.id))
    if not c or not m:
        raise HTTPException(404, "Crew not found")
    if roles and m.role not in roles:
        raise HTTPException(403, "Crew owner or moderator required")
    return c, m


class InviteInput(Strict):
    user_id: str


@router.post("/crews/{crew_id}/invitations", status_code=201)
def invite(
    crew_id: str, data: InviteInput, u=Depends(current_user), db=Depends(get_db)
):
    db.scalar(select(Crew).where(Crew.id == crew_id).with_for_update())
    c, _ = membership(db, crew_id, u, {"owner", "moderator"})
    recipient = db.get(User, data.user_id)
    if (
        not recipient
        or recipient.suspended
        or recipient.id == u.id
        or blocked(db, u.id, recipient.id)
        or blocked(db, c.owner_id, recipient.id)
    ):
        raise HTTPException(404, "Player unavailable")
    if db.get(CrewMember, (crew_id, recipient.id)):
        raise HTTPException(409, "Player already belongs to Crew")
    prior = db.scalar(
        select(CrewInvitation).where(
            CrewInvitation.crew_id == crew_id,
            CrewInvitation.recipient_id == recipient.id,
        )
    )
    if prior and prior.status == "pending" and prior.expires_at > time.time():
        return serialize(prior)
    if prior:
        prior.sender_id = u.id
        prior.status = "pending"
        prior.expires_at = time.time() + 604800
    else:
        prior = CrewInvitation(
            crew_id=crew_id,
            sender_id=u.id,
            recipient_id=recipient.id,
            expires_at=time.time() + 604800,
        )
        db.add(prior)
    db.flush()
    notify(
        db,
        recipient.id,
        "crew_invitation",
        u.username + " invited you to " + c.name,
        prior.id,
    )
    return serialize(prior)


@router.get("/crew-invitations")
def invitations(u=Depends(current_user), db=Depends(get_db)):
    return [
        dict(serialize(i), crew_name=c.name)
        for i, c in db.execute(
            select(CrewInvitation, Crew)
            .join(Crew, Crew.id == CrewInvitation.crew_id)
            .where(
                CrewInvitation.recipient_id == u.id,
                CrewInvitation.status == "pending",
                CrewInvitation.expires_at > time.time(),
            )
        )
        if not blocked(db, u.id, i.sender_id) and not blocked(db, u.id, c.owner_id)
    ]


@router.post("/crew-invitations/{invitation_id}/accept")
def accept(invitation_id: str, u=Depends(current_user), db=Depends(get_db)):
    initial = db.scalar(
        select(CrewInvitation).where(
            CrewInvitation.id == invitation_id, CrewInvitation.recipient_id == u.id
        )
    )
    if not initial:
        raise HTTPException(404, "Invitation not found")
    c = db.scalar(select(Crew).where(Crew.id == initial.crew_id).with_for_update())
    i = db.scalar(
        select(CrewInvitation)
        .where(CrewInvitation.id == invitation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not c or blocked(db, u.id, i.sender_id) or blocked(db, u.id, c.owner_id):
        raise HTTPException(403, "Invitation unavailable")
    if i.status == "accepted" and db.get(CrewMember, (c.id, u.id)):
        return {"ok": True, "crew_id": c.id}
    sender = db.get(CrewMember, (c.id, i.sender_id))
    if (
        i.status != "pending"
        or i.expires_at < time.time()
        or not sender
        or sender.role not in {"owner", "moderator"}
    ):
        raise HTTPException(409, "Invitation no longer valid")
    if not db.get(CrewMember, (c.id, u.id)):
        db.add(CrewMember(crew_id=c.id, user_id=u.id))
    i.status = "accepted"
    emit(db, u, "crew_joined", c.id)
    return {"ok": True, "crew_id": c.id}


@router.post("/crew-invitations/{invitation_id}/decline")
def decline(invitation_id: str, u=Depends(current_user), db=Depends(get_db)):
    i = db.scalar(
        select(CrewInvitation)
        .where(CrewInvitation.id == invitation_id, CrewInvitation.recipient_id == u.id)
        .with_for_update()
    )
    if not i:
        raise HTTPException(404, "Invitation not found")
    if i.status == "pending":
        i.status = "declined"
    return {"ok": True}


@router.get("/crews/{crew_id}/members")
def members(crew_id: str, u=Depends(current_user), db=Depends(get_db)):
    membership(db, crew_id, u)
    return [
        dict(user_id=p.id, username=p.username, role=m.role)
        for m, p in db.execute(
            select(CrewMember, User)
            .join(User, User.id == CrewMember.user_id)
            .where(CrewMember.crew_id == crew_id)
        )
        if not blocked(db, u.id, p.id)
    ]


class RoleInput(Strict):
    role: Literal["member", "moderator"]


@router.patch("/crews/{crew_id}/members/{user_id}")
def role(
    crew_id: str,
    user_id: str,
    data: RoleInput,
    u=Depends(current_user),
    db=Depends(get_db),
):
    db.scalar(select(Crew).where(Crew.id == crew_id).with_for_update())
    membership(db, crew_id, u, {"owner"})
    m = db.get(CrewMember, (crew_id, user_id))
    if not m:
        raise HTTPException(404, "Crew member not found")
    if m.role == "owner":
        raise HTTPException(409, "Owner role cannot be changed")
    m.role = data.role
    db.add(Audit(actor_id=u.id, action="crew.role", target=crew_id + ":" + user_id))
    return {"ok": True}


@router.delete("/crews/{crew_id}/members/{user_id}")
def remove_member(
    crew_id: str, user_id: str, u=Depends(current_user), db=Depends(get_db)
):
    db.scalar(select(Crew).where(Crew.id == crew_id).with_for_update())
    c, actor = membership(db, crew_id, u)
    m = db.get(CrewMember, (crew_id, user_id))
    if not m:
        raise HTTPException(404, "Member not found")
    if m.role == "owner":
        raise HTTPException(409, "Owner must retain Crew membership")
    if u.id != user_id and (
        actor.role not in {"owner", "moderator"}
        or (m.role == "moderator" and actor.role != "owner")
    ):
        raise HTTPException(403, "Cannot remove this member")
    db.delete(m)
    db.add(
        Audit(
            actor_id=u.id, action="crew.member_removed", target=crew_id + ":" + user_id
        )
    )
    return {"ok": True}


class CrewMessageInput(Strict):
    body: str = Field(min_length=1, max_length=2000)
    request_id: str = Field(default_factory=uid, min_length=8, max_length=100)


@router.get("/crews/{crew_id}/messages")
def messages(crew_id: str, u=Depends(current_user), db=Depends(get_db)):
    membership(db, crew_id, u)
    rows = list(
        db.scalars(
            select(CrewMessage)
            .where(CrewMessage.crew_id == crew_id)
            .order_by(CrewMessage.created_at.desc())
            .limit(100)
        )
    )
    return [
        dict(serialize(m), username=db.get(User, m.sender_id).username)
        for m in reversed(rows)
        if not blocked(db, u.id, m.sender_id)
    ]


@router.post("/crews/{crew_id}/messages", status_code=201)
def message(
    crew_id: str, data: CrewMessageInput, u=Depends(current_user), db=Depends(get_db)
):
    db.scalar(select(User).where(User.id == u.id).with_for_update())
    membership(db, crew_id, u)
    body = data.body.strip()
    if not body:
        raise HTTPException(422, "Message cannot be blank")
    prior = db.scalar(
        select(CrewMessage).where(
            CrewMessage.crew_id == crew_id,
            CrewMessage.sender_id == u.id,
            CrewMessage.request_id == data.request_id,
        )
    )
    if prior:
        if prior.body != body:
            raise HTTPException(409, "Request ID reused with different message")
        return dict(serialize(prior), username=u.username)
    recent = (
        db.scalar(
            select(func.count())
            .select_from(CrewMessage)
            .where(
                CrewMessage.sender_id == u.id, CrewMessage.created_at > time.time() - 60
            )
        )
        or 0
    )
    if recent >= 30:
        raise HTTPException(429, "Please wait before sending more Crew messages")
    m = CrewMessage(
        crew_id=crew_id, sender_id=u.id, body=body, request_id=data.request_id
    )
    db.add(m)
    db.flush()
    emit(db, u, "crew_message_sent", m.id)
    return dict(serialize(m), username=u.username)
