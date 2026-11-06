"""Virtual entitlements. All ownership and wallet writes share one transaction."""

import time
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import ForeignKey, String, JSON, select, update, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from .db import Base, get_db
from .auth import current_user
from .core import Strict
from .models import User, Notification, uid
from .operations import audit, super_admin
from .growth import require_access, require_open
from .economy import balance, credit
from .world import blocked
from .property_inventory import inventory, outlines

router = APIRouter(prefix="/api/properties")


class Property(Base):
    __tablename__ = "virtual_properties"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    city: Mapped[str] = mapped_column(String(50), index=True)
    category: Mapped[str]
    title: Mapped[str]
    x: Mapped[float]
    z: Mapped[float]
    owner: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    generation: Mapped[int] = mapped_column(default=0)
    name: Mapped[str] = mapped_column(default="")
    style: Mapped[dict] = mapped_column(JSON, default=dict)
    acquired: Mapped[float | None]
    cost: Mapped[int | None]


class Price(Base):
    __tablename__ = "virtual_property_prices"
    scope: Mapped[str] = mapped_column(String(120), primary_key=True)
    category: Mapped[str] = mapped_column(String(40), primary_key=True)
    xp: Mapped[int]
    enabled: Mapped[bool]


class Trade(Base):
    __tablename__ = "virtual_property_trades"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    property_id: Mapped[str] = mapped_column(ForeignKey(Property.id), index=True)
    buyer: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    seller: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int]
    request_key: Mapped[str]
    created: Mapped[float] = mapped_column(default=time.time)
    __table_args__ = (UniqueConstraint("buyer", "request_key"),)


class Offer(Base):
    __tablename__ = "virtual_property_offers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    property_id: Mapped[str] = mapped_column(ForeignKey(Property.id), index=True)
    buyer: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    seller: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int]
    generation: Mapped[int]
    state: Mapped[str]
    expires: Mapped[float]


def register(db, city):
    require_open(db, city)
    rows = inventory(city)
    existing = set(db.scalars(select(Property.id).where(Property.city == city)))
    missing = [row for key, row in rows.items() if key not in existing]
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    for i in range(0, len(missing), 100):
        db.execute(
            insert(Property)
            .values(missing[i : i + 100])
            .on_conflict_do_nothing(index_elements=["id"])
        )
    return len(rows)


def pricing(db, p):
    from .expansion import Destination

    country = db.get(Destination, p.city).country
    for scope in (p.id, p.city, country, "*"):
        rule = db.get(Price, (scope, p.category))
        if rule:
            return rule.xp, rule.enabled
    return 2000, p.category != "venue"


def view(db, p, u):
    xp, enabled = pricing(db, p)
    from .public_profiles import visible

    owner = db.get(User, p.owner) if p.owner else None
    display = owner.username if owner and visible(db, u, owner) else None
    return dict(
        owner_id=owner.id if display else None,
        owner=display,
        id=p.id,
        city=p.city,
        category=p.category,
        name=p.name or p.title,
        x=p.x,
        z=p.z,
        owned=p.owner is not None,
        mine=p.owner == u.id,
        price=xp,
        enabled=enabled,
        style={k: v for k, v in p.style.items() if k != "guests" or p.owner == u.id},
        cost=p.cost if p.owner == u.id else None,
        acquired=p.acquired if p.owner == u.id else None,
    )


def locked_property(db, key):
    p = db.scalar(select(Property).where(Property.id == key).with_for_update())
    if not p or key not in inventory(p.city):
        raise HTTPException(404, "Property unavailable")
    return p


class Purchase(Strict):
    amount: int = Field(gt=0, le=1_000_000_000, strict=True)
    request_key: UUID


def transfer(db, p, buyer, seller, amount, key):
    parties = [buyer] if seller is None else sorted([buyer, seller])
    users = list(
        db.scalars(
            select(User).where(User.id.in_(parties)).order_by(User.id).with_for_update()
        )
    )
    if len(users) != len(parties) or any(u.suspended for u in users):
        raise HTTPException(403, "Account unavailable")
    available = balance(db, buyer, "xp")
    if available < amount:
        raise HTTPException(
            409,
            dict(
                code="INSUFFICIENT_XP",
                balance=available,
                shortfall=amount - available,
                message=f"You need another {amount - available} XP to claim this property.",
            ),
        )
    t = Trade(
        property_id=p.id, buyer=buyer, seller=seller, amount=amount, request_key=key
    )
    db.add(t)
    db.flush()
    credit(db, buyer, -amount, "property_purchase", p.id, "property:" + t.id, "xp")
    if seller:
        credit(db, seller, amount, "property_sale", p.id, "property:" + t.id, "xp")
    p.owner, p.cost, p.acquired = buyer, amount, time.time()
    p.generation += 1
    p.name, p.style = "", {}
    ensure_private_interior(db, p)
    db.execute(
        update(Offer)
        .where(Offer.property_id == p.id, Offer.state.in_(["pending", "countered"]))
        .values(state="superseded")
    )
    audit(
        db,
        db.get(User, buyer),
        "property.transfer",
        p.id,
        {"receipt": t.id, "amount": amount, "seller": seller},
    )
    return t


@router.get("/city/{city}")
def browse(city: str, u=Depends(current_user), db=Depends(get_db), offset: int = 0):
    require_access(db, u, city)
    register(db, city)
    from .models import Presence

    presence = db.get(Presence, u.id)
    q = select(Property).where(Property.city == city)
    if presence and presence.city == city:
        dx, dz = Property.x - presence.x, Property.z - presence.z
        q = q.order_by(dx * dx + dz * dz)
    rows = db.scalars(q.order_by(Property.id).offset(max(0, offset)).limit(48))
    return {
        "items": [view(db, p, u) for p in rows if p.id in inventory(city)],
        "balance": balance(db, u.id, "xp"),
    }


@router.get("/portfolio")
def portfolio(u=Depends(current_user), db=Depends(get_db)):
    return [
        view(db, p, u)
        for p in db.scalars(
            select(Property)
            .where(Property.owner == u.id)
            .order_by(Property.acquired.desc())
        )
    ]


@router.post("/{key}/claim")
def purchase(key: str, data: Purchase, u=Depends(current_user), db=Depends(get_db)):
    p = locked_property(db, key)
    require_access(db, u, p.city)
    request_key = str(data.request_key)
    db.scalar(select(User.id).where(User.id == u.id).with_for_update())
    old = db.scalar(
        select(Trade).where(Trade.buyer == u.id, Trade.request_key == request_key)
    )
    if old:
        if old.property_id != key or old.amount != data.amount or old.seller:
            raise HTTPException(409, "Purchase reference conflict")
        return {"receipt": old.id, "balance": balance(db, u.id, "xp")}
    rules = policy(db)
    if not rules.purchase or balance(db, u.id, "xp") < rules.minimum_xp:
        raise HTTPException(409, "Property purchases or XP eligibility restricted")
    recent = db.scalar(
        select(func.count(Trade.id)).where(
            Trade.buyer == u.id, Trade.created > time.time() - 3600
        )
    )
    if recent >= rules.hourly_claims:
        raise HTTPException(429, "Hourly property limit reached")
    price, enabled = pricing(db, p)
    if p.owner or not enabled or price != data.amount:
        raise HTTPException(
            409, "Availability or price changed. Review the property again."
        )
    trade = transfer(db, p, u.id, None, price, request_key)
    return {"receipt": trade.id, "balance": balance(db, u.id, "xp")}


class Bid(Strict):
    amount: int = Field(gt=0, le=1_000_000_000, strict=True)


def notify(db, user, msg, key):
    db.add(Notification(user_id=user, kind="property", body=msg, source=key))


@router.post("/{key}/offer")
def offer(key: str, data: Bid, u=Depends(current_user), db=Depends(get_db)):
    p = locked_property(db, key)
    require_access(db, u, p.city)
    if not policy(db).resale:
        raise HTTPException(409, "Property resale paused")
    if not p.owner or p.owner == u.id or blocked(db, u.id, p.owner):
        raise HTTPException(403, "Offer unavailable")
    db.scalar(select(User.id).where(User.id == u.id).with_for_update())
    recent_count = db.scalar(
        select(func.count(Offer.id)).where(
            Offer.buyer == u.id, Offer.expires > time.time() + 7 * 86400 - 3600
        )
    )
    if recent_count >= 20:
        raise HTTPException(429, "Hourly offer limit reached")
    if balance(db, u.id, "xp") < data.amount:
        raise HTTPException(409, "Insufficient spendable XP")
    active = select(Offer.id).where(
        Offer.property_id == key,
        Offer.buyer == u.id,
        Offer.state.in_(["pending", "countered"]),
        Offer.expires > time.time(),
    )
    if db.scalar(active):
        raise HTTPException(409, "You already have an open offer")
    bid = Offer(
        property_id=key,
        buyer=u.id,
        seller=p.owner,
        amount=data.amount,
        generation=p.generation,
        state="pending",
        expires=time.time() + 7 * 86400,
    )
    db.add(bid)
    db.flush()
    notify(db, p.owner, "You received an XP offer for " + (p.name or p.title), bid.id)
    return {"id": bid.id}


@router.get("/offers")
def offers(u=Depends(current_user), db=Depends(get_db)):
    q = (
        select(Offer)
        .where((Offer.buyer == u.id) | (Offer.seller == u.id))
        .order_by(Offer.expires.desc())
    )
    return [
        dict(
            id=o.id,
            property_id=o.property_id,
            amount=o.amount,
            incoming=o.seller == u.id,
            state="expired"
            if o.state in ("pending", "countered") and o.expires <= time.time()
            else o.state,
        )
        for o in db.scalars(q)
    ]


class Decision(Strict):
    action: Literal["accept", "reject", "counter"]
    amount: int | None = Field(default=None, gt=0, le=1_000_000_000, strict=True)
    expected_amount: int = Field(gt=0, le=1_000_000_000, strict=True)


@router.post("/offers/{bid_id}")
def decide(bid_id: str, data: Decision, u=Depends(current_user), db=Depends(get_db)):
    key = db.scalar(select(Offer.property_id).where(Offer.id == bid_id))
    p = locked_property(db, key)
    o = db.scalar(select(Offer).where(Offer.id == bid_id).with_for_update())
    if (
        o.state not in ("pending", "countered")
        or o.expires <= time.time()
        or p.owner != o.seller
        or p.generation != o.generation
        or data.expected_amount != o.amount
    ):
        raise HTTPException(409, "Offer has changed or expired")
    actor = o.seller if o.state == "pending" else o.buyer
    if u.id != actor or blocked(db, o.buyer, o.seller):
        raise HTTPException(403, "Offer unavailable")
    require_access(db, u, p.city)
    if data.action == "counter":
        if u.id != o.seller or not data.amount:
            raise HTTPException(422, "Enter a counteroffer amount")
        o.amount, o.state = data.amount, "countered"
    elif data.action == "reject":
        o.state = "rejected"
    else:
        if not policy(db).resale:
            raise HTTPException(409, "Property resale paused")
        require_access(db, db.get(User, o.buyer), p.city)
        transfer(db, p, o.buyer, o.seller, o.amount, "offer:" + o.id)
        o.state = "accepted"
    notify(
        db, o.buyer if u.id == o.seller else o.seller, "Property offer " + o.state, o.id
    )
    audit(db, u, "property.offer." + o.state, key, {"offer": o.id, "amount": o.amount})
    return {"state": o.state}


@router.get("/history")
def history(u=Depends(current_user), db=Depends(get_db)):
    rows = db.scalars(
        select(Trade)
        .where((Trade.buyer == u.id) | (Trade.seller == u.id))
        .order_by(Trade.created.desc())
    )
    return [
        dict(
            id=t.id,
            property_id=t.property_id,
            xp=t.amount,
            action="acquired" if t.buyer == u.id else "sold",
            date=t.created,
        )
        for t in rows
    ]


class Pricing(Bid):
    scope: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=40)
    enabled: bool


@router.put("/admin/prices")
def set_price(data: Pricing, u=Depends(super_admin), db=Depends(get_db)):
    db.merge(
        Price(
            scope=data.scope,
            category=data.category,
            xp=data.amount,
            enabled=data.enabled,
        )
    )
    audit(db, u, "property.price", data.scope, data.model_dump())
    return {"saved": True}


@router.get("/admin/coverage")
def coverage(u=Depends(super_admin), db=Depends(get_db)):
    from .discovery import catalog

    cities = [
        c
        for c in catalog(db)
        if all(c.get(k) for k in ("enabled", "public", "joinable"))
    ]
    counts = dict(
        db.execute(
            select(Property.city, func.count(Property.id)).group_by(Property.city)
        ).all()
    )
    return [
        dict(
            city=c["id"],
            eligible=len(inventory(c["id"])),
            registered=counts.get(c["id"], 0),
        )
        for c in cities
    ]


@router.post("/admin/register/{city}")
def register_city(city: str, u=Depends(super_admin), db=Depends(get_db)):
    count = register(db, city)
    audit(db, u, "property.register", city, {"eligible": count})
    return {"eligible": count}


def neighborhood(db, city, x, z):
    from .property_inventory import nearby

    rows = nearby(city, x, z)
    if not rows:
        return []
    owned = {
        p.id: p
        for p in db.scalars(
            select(Property).where(
                Property.id.in_([r["id"] for r in rows]), Property.owner.is_not(None)
            )
        )
    }
    return [
        dict(
            id=r["id"],
            x=r["x"],
            z=r["z"],
            name=(owned[r["id"]].name or r["title"])
            if r["id"] in owned
            else r["title"],
            owned=r["id"] in owned,
            colors=owned[r["id"]].style.get("colors", {}) if r["id"] in owned else {},
            color=owned[r["id"]].style.get("board", "navy")
            if r["id"] in owned
            else "navy",
        )
        for r in rows
    ]


@router.get("/detail/{key}")
def detail(key: str, u=Depends(current_user), db=Depends(get_db)):
    city = key.partition(":")[0]
    require_access(db, u, city)
    if key not in inventory(city):
        raise HTTPException(404, "This building is unavailable")
    p = db.get(Property, key)
    if not p:
        register(db, city)
        p = db.get(Property, key)
    return {
        **view(db, p, u),
        "outline": outlines(city).get(key,[]),
        "may_enter": bool(p.owner and may_visit(db, p, u) and p.category != "venue"),
        "balance": balance(db, u.id, "xp"),
    }


class Studio(Strict):
    name: str = Field(min_length=2, max_length=48)
    board: Literal["navy", "forest", "burgundy"]
    description: str = Field(max_length=220, default="")
    access: Literal["private", "friends", "invite", "public"] = "private"
    colors: dict[
        Literal["wall", "roof", "trim", "door", "window"],
        Literal["#e9dcc7", "#bd8d74", "#234e51", "#405670", "#f0eedc", "#634854"],
    ] = Field(default_factory=dict)
    guests: list[UUID] = Field(default_factory=list, max_length=32)


@router.patch("/{key}/studio")
def publish(key: str, data: Studio, u=Depends(current_user), db=Depends(get_db)):
    import re, unicodedata

    p = locked_property(db, key)
    if p.owner != u.id:
        raise HTTPException(403, "Only the owner can publish changes")
    name = unicodedata.normalize("NFKC", data.name).strip()
    if (
        len(name) < 2
        or not re.fullmatch(r"[\w .’'&-]+", name)
        or re.search(r"\b(admin|moderator|mindaam support|fuck|shit)\b", name, re.I)
    ):
        raise HTTPException(422, "Choose a different property name")
    p.name = name
    p.style = {
        "colors": data.colors,
        "board": data.board,
        "description": data.description.strip(),
        "access": data.access,
        "guests": list(map(str, data.guests)) if data.access == "invite" else [],
    }
    ensure_private_interior(db, p)
    audit(db, u, "property.publish", key, {"generation": p.generation})
    return view(db, p, u)


def may_visit(db, p, u):
    from .world import friends

    if u.id == p.owner:
        return True
    if not p.owner or blocked(db, p.owner, u.id):
        return False
    access = p.style.get("access", "private")
    return (
        access == "public"
        or (access == "friends" and friends(db, p.owner, u.id))
        or (access == "invite" and u.id in p.style.get("guests", []))
    )


@router.get("/admin/overview")
def overview(u=Depends(super_admin), db=Depends(get_db)):
    count = lambda c: db.scalar(select(func.count(c)))
    total = count(Property.id)
    owned = count(Property.owner)

    def volume(condition):
        return db.scalar(
            select(func.coalesce(func.sum(Trade.amount), 0)).where(condition)
        )

    return dict(
        registered=total,
        available=total - owned,
        owned=owned,
        owners=count(func.distinct(Property.owner)),
        claims_xp=volume(Trade.seller.is_(None)),
        resales_xp=volume(Trade.seller.is_not(None)),
        pending=db.scalar(
            select(func.count(Offer.id)).where(
                Offer.state.in_(["pending", "countered"]), Offer.expires > time.time()
            )
        ),
    )


def ensure_private_interior(db, p):
    from .civic import PublicBuilding, entrance
    from .geography import nearest_safe_position

    if p.category == "venue":
        return None
    key = "home:" + p.id
    interior = db.get(PublicBuilding, key)
    if interior:
        interior.name = p.name or p.title
        return interior
    point = nearest_safe_position(p.city, p.x, p.z) or entrance(p.city,(p.x,p.z))
    if point is None:
        return None
    interior = PublicBuilding(
        id=key,
        city=p.city,
        name=p.name or p.title,
        source_id=p.id,
        template="reception",
        x=point[0],
        z=point[1],
        enabled=True,
    )
    db.add(interior)
    db.flush()
    return interior


class EconomyPolicy(Strict):
    purchase: bool = True
    resale: bool = True
    minimum_xp: int = Field(default=0, ge=0, le=1_000_000_000)
    hourly_claims: int = Field(default=30, ge=1, le=1000)


def policy(db):
    from .economy import config

    return EconomyPolicy(**config(db, "virtual_property_policy", {}))


@router.get("/admin/policy")
def get_policy(u=Depends(super_admin), db=Depends(get_db)):
    return policy(db)


@router.put("/admin/policy")
def configure(data: EconomyPolicy, u=Depends(super_admin), db=Depends(get_db)):
    from .models import Config

    db.merge(Config(key="virtual_property_policy", value=data.model_dump()))
    audit(db, u, "property.policy", "virtual_property_policy", data.model_dump())
    return data


@router.get("/admin/records/{kind}")
def records(
    kind: Literal[
        "inventory", "owners", "trades", "offers", "audit", "prices", "venues"
    ],
    offset: int = 0,
    u=Depends(super_admin),
    db=Depends(get_db),
):
    from .models import Audit
    from .core import serialize

    if kind in ("inventory", "owners", "venues"):
        q = select(Property).order_by(Property.city, Property.id)
        if kind == "owners":
            q = q.where(Property.owner.is_not(None))
        if kind == "venues":
            q = q.where(Property.category == "venue")
    elif kind == "offers":
        q = select(Offer).order_by(Offer.expires.desc())
    elif kind == "audit":
        q = (
            select(Audit)
            .where(Audit.action.like("property.%"))
            .order_by(Audit.created_at.desc())
        )
    elif kind == "trades":
        q = select(Trade).order_by(Trade.created.desc())
    else:
        q = select(Price).order_by(Price.scope, Price.category)
    return [serialize(row) for row in db.scalars(q.offset(max(0, offset)).limit(50))]


@router.get("/achievements")
def achievements(u=Depends(current_user), db=Depends(get_db)):
    purchases = db.scalar(select(func.count(Trade.id)).where(Trade.buyer == u.id))
    cities = db.scalar(
        select(func.count(func.distinct(Property.city)))
        .join(Trade, Trade.property_id == Property.id)
        .where(Trade.buyer == u.id)
    )
    return [
        dict(name=name, earned=value >= goal, progress=value, goal=goal)
        for name, value, goal in (
            ("Property owner", purchases, 1),
            ("Property collector", purchases, 5),
            ("Three-city portfolio", cities, 3),
        )
    ]
