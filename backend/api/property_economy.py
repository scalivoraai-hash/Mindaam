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
from .property_inventory import inventory

router = APIRouter(prefix='/api/properties')

class Property(Base):
    __tablename__ = 'virtual_properties'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    city: Mapped[str] = mapped_column(String(50), index=True)
    category: Mapped[str]
    title: Mapped[str]
    x: Mapped[float]
    z: Mapped[float]
    owner: Mapped[str | None] = mapped_column(ForeignKey('users.id'), index=True)
    generation: Mapped[int] = mapped_column(default=0)
    name: Mapped[str] = mapped_column(default='')
    style: Mapped[dict] = mapped_column(JSON, default=dict)
    acquired: Mapped[float | None]
    cost: Mapped[int | None]

class Price(Base):
    __tablename__ = 'virtual_property_prices'
    scope: Mapped[str] = mapped_column(String(120), primary_key=True)
    category: Mapped[str] = mapped_column(String(40), primary_key=True)
    xp: Mapped[int]
    enabled: Mapped[bool]

class Trade(Base):
    __tablename__ = 'virtual_property_trades'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    property_id: Mapped[str] = mapped_column(ForeignKey(Property.id), index=True)
    buyer: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    seller: Mapped[str | None] = mapped_column(ForeignKey('users.id'), index=True)
    amount: Mapped[int]
    request_key: Mapped[str]
    created: Mapped[float] = mapped_column(default=time.time)
    __table_args__ = (UniqueConstraint('buyer','request_key'),)

class Offer(Base):
    __tablename__ = 'virtual_property_offers'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    property_id: Mapped[str] = mapped_column(ForeignKey(Property.id), index=True)
    buyer: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    seller: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    amount: Mapped[int]
    generation: Mapped[int]
    state: Mapped[str]
    expires: Mapped[float]

def register(db,city):
    require_open(db,city)
    rows = inventory(city)
    existing = set(db.scalars(select(Property.id).where(Property.city==city)))
    missing = [row for key,row in rows.items() if key not in existing]
    insert = pg_insert if db.get_bind().dialect.name=='postgresql' else sqlite_insert
    for i in range(0,len(missing),100):
        db.execute(insert(Property).values(missing[i:i+100]).on_conflict_do_nothing(index_elements=['id']))
    return len(rows)

def pricing(db,p):
    from .expansion import Destination
    country = db.get(Destination,p.city).country
    for scope in (p.id,p.city,country,'*'):
        rule = db.get(Price,(scope,p.category))
        if rule:
            return rule.xp,rule.enabled
    return 2000,True

def view(db,p,u):
    xp,enabled = pricing(db,p)
    from .public_profiles import visible
    owner=db.get(User,p.owner) if p.owner else None
    display=owner.username if owner and visible(db,u,owner) else None
    return dict(owner=display,id=p.id,city=p.city,category=p.category,name=p.name or p.title,x=p.x,z=p.z,
                owned=p.owner is not None,mine=p.owner==u.id,price=xp,enabled=enabled,
                style={k:v for k,v in p.style.items() if k!='guests' or p.owner==u.id},cost=p.cost if p.owner==u.id else None,acquired=p.acquired if p.owner==u.id else None)

def locked_property(db,key):
    p=db.scalar(select(Property).where(Property.id==key).with_for_update())
    if not p or key not in inventory(p.city):
        raise HTTPException(404,'Property unavailable')
    return p

class Purchase(Strict):
    amount: int = Field(gt=0,le=1_000_000_000,strict=True)
    request_key: UUID

def transfer(db,p,buyer,seller,amount,key):
    parties=[buyer] if seller is None else sorted([buyer,seller])
    users=list(db.scalars(select(User).where(User.id.in_(parties)).order_by(User.id).with_for_update()))
    if len(users)!=len(parties) or any(u.suspended for u in users):
        raise HTTPException(403,'Account unavailable')
    available=balance(db,buyer,'xp')
    if available<amount:
        raise HTTPException(409,dict(code='INSUFFICIENT_XP',balance=available,shortfall=amount-available,
                                    message=f'You need another {amount-available} XP to claim this property.'))
    t=Trade(property_id=p.id,buyer=buyer,seller=seller,amount=amount,request_key=key)
    db.add(t)
    db.flush()
    credit(db,buyer,-amount,'property_purchase',p.id,'property:'+t.id,'xp')
    if seller:
        credit(db,seller,amount,'property_sale',p.id,'property:'+t.id,'xp')
    p.owner,p.cost,p.acquired=buyer,amount,time.time()
    p.generation+=1
    p.name,p.style='',{}
    db.execute(update(Offer).where(Offer.property_id==p.id,Offer.state.in_(['pending','countered'])).values(state='superseded'))
    return t

@router.get('/city/{city}')
def browse(city:str,u=Depends(current_user),db=Depends(get_db),offset:int=0):
    require_access(db,u,city)
    register(db,city)
    from .models import Presence
    presence=db.get(Presence,u.id)
    q=select(Property).where(Property.city==city)
    if presence and presence.city==city:
        dx,dz=Property.x-presence.x,Property.z-presence.z
        q=q.order_by(dx*dx+dz*dz)
    rows=db.scalars(q.order_by(Property.id).offset(max(0,offset)).limit(48))
    return {'items':[view(db,p,u) for p in rows if p.id in inventory(city)],'balance':balance(db,u.id,'xp')}

@router.get('/portfolio')
def portfolio(u=Depends(current_user),db=Depends(get_db)):
    return [view(db,p,u) for p in db.scalars(select(Property).where(Property.owner==u.id).order_by(Property.acquired.desc()))]

@router.post('/{key}/claim')
def purchase(key:str,data:Purchase,u=Depends(current_user),db=Depends(get_db)):
    p=locked_property(db,key)
    require_access(db,u,p.city)
    request_key=str(data.request_key)
    old=db.scalar(select(Trade).where(Trade.buyer==u.id,Trade.request_key==request_key))
    if old:
        if old.property_id!=key or old.amount!=data.amount or old.seller:
            raise HTTPException(409,'Purchase reference conflict')
        return {'receipt':old.id,'balance':balance(db,u.id,'xp')}
    price,enabled=pricing(db,p)
    if p.owner or not enabled or price!=data.amount:
        raise HTTPException(409,'Availability or price changed. Review the property again.')
    trade=transfer(db,p,u.id,None,price,request_key)
    return {'receipt':trade.id,'balance':balance(db,u.id,'xp')}

class Bid(Strict):
    amount:int=Field(gt=0,le=1_000_000_000,strict=True)

def notify(db,user,msg,key):
    db.add(Notification(user_id=user,kind='property',body=msg,source=key))

@router.post('/{key}/offer')
def offer(key:str,data:Bid,u=Depends(current_user),db=Depends(get_db)):
    p=locked_property(db,key)
    require_access(db,u,p.city)
    if not p.owner or p.owner==u.id or blocked(db,u.id,p.owner):
        raise HTTPException(403,'Offer unavailable')
    if balance(db,u.id,'xp')<data.amount:
        raise HTTPException(409,'Insufficient spendable XP')
    active=select(Offer.id).where(Offer.property_id==key,Offer.buyer==u.id,
                                 Offer.state.in_(['pending','countered']),Offer.expires>time.time())
    if db.scalar(active):
        raise HTTPException(409,'You already have an open offer')
    bid=Offer(property_id=key,buyer=u.id,seller=p.owner,amount=data.amount,generation=p.generation,
              state='pending',expires=time.time()+7*86400)
    db.add(bid)
    db.flush()
    notify(db,p.owner,'You received an XP offer for '+(p.name or p.title),bid.id)
    return {'id':bid.id}

@router.get('/offers')
def offers(u=Depends(current_user),db=Depends(get_db)):
    q=select(Offer).where((Offer.buyer==u.id)|(Offer.seller==u.id)).order_by(Offer.expires.desc())
    return [dict(id=o.id,property_id=o.property_id,amount=o.amount,incoming=o.seller==u.id,
                 state='expired' if o.state in ('pending','countered') and o.expires<=time.time() else o.state)
            for o in db.scalars(q)]

class Decision(Strict):
    action: Literal['accept','reject','counter']
    amount: int|None=Field(default=None,gt=0,le=1_000_000_000,strict=True)
    expected_amount:int=Field(gt=0,le=1_000_000_000,strict=True)

@router.post('/offers/{bid_id}')
def decide(bid_id:str,data:Decision,u=Depends(current_user),db=Depends(get_db)):
    key=db.scalar(select(Offer.property_id).where(Offer.id==bid_id))
    p=locked_property(db,key)
    o=db.scalar(select(Offer).where(Offer.id==bid_id).with_for_update())
    if o.state not in ('pending','countered') or o.expires<=time.time() or p.owner!=o.seller or p.generation!=o.generation or data.expected_amount!=o.amount:
        raise HTTPException(409,'Offer has changed or expired')
    actor=o.seller if o.state=='pending' else o.buyer
    if u.id!=actor or blocked(db,o.buyer,o.seller):
        raise HTTPException(403,'Offer unavailable')
    require_access(db,u,p.city)
    if data.action=='counter':
        if u.id!=o.seller or not data.amount:
            raise HTTPException(422,'Enter a counteroffer amount')
        o.amount,o.state=data.amount,'countered'
    elif data.action=='reject':
        o.state='rejected'
    else:
        require_access(db,db.get(User,o.buyer),p.city)
        transfer(db,p,o.buyer,o.seller,o.amount,'offer:'+o.id)
        o.state='accepted'
    notify(db,o.buyer if u.id==o.seller else o.seller,'Property offer '+o.state,o.id)
    audit(db,u,'property.offer.'+o.state,key,{'offer':o.id,'amount':o.amount})
    return {'state':o.state}

@router.get('/history')
def history(u=Depends(current_user),db=Depends(get_db)):
    rows=db.scalars(select(Trade).where((Trade.buyer==u.id)|(Trade.seller==u.id)).order_by(Trade.created.desc()))
    return [dict(id=t.id,property_id=t.property_id,xp=t.amount,action='acquired' if t.buyer==u.id else 'sold',date=t.created) for t in rows]

class Pricing(Bid):
    scope:str=Field(min_length=1,max_length=100)
    category:str=Field(min_length=1,max_length=40)
    enabled:bool

@router.put('/admin/prices')
def set_price(data:Pricing,u=Depends(super_admin),db=Depends(get_db)):
    db.merge(Price(scope=data.scope,category=data.category,xp=data.amount,enabled=data.enabled))
    audit(db,u,'property.price',data.scope,data.model_dump())
    return {'saved':True}

@router.get('/admin/coverage')
def coverage(u=Depends(super_admin),db=Depends(get_db)):
    from .discovery import catalog
    cities=[c for c in catalog(db) if all(c.get(k) for k in ('enabled','public','joinable'))]
    counts=dict(db.execute(select(Property.city,func.count(Property.id)).group_by(Property.city)).all())
    return [dict(city=c['id'],eligible=len(inventory(c['id'])),registered=counts.get(c['id'],0)) for c in cities]

@router.post('/admin/register/{city}')
def register_city(city:str,u=Depends(super_admin),db=Depends(get_db)):
    count=register(db,city)
    audit(db,u,'property.register',city,{'eligible':count})
    return {'eligible':count}

def neighborhood(db,city,x,z):
    from .property_inventory import nearby
    rows=nearby(city,x,z)
    if not rows:
        return []
    owned={p.id:p for p in db.scalars(select(Property).where(Property.id.in_([r['id'] for r in rows]),Property.owner.is_not(None)))}
    return [dict(id=r['id'],x=r['x'],z=r['z'],name=(owned[r['id']].name or r['title']) if r['id'] in owned else r['title'],
                 owned=r['id'] in owned,color=owned[r['id']].style.get('board','navy') if r['id'] in owned else 'navy') for r in rows]

@router.get('/detail/{key}')
def detail(key:str,u=Depends(current_user),db=Depends(get_db)):
    city=key.partition(':')[0]
    require_access(db,u,city)
    if key not in inventory(city):
        raise HTTPException(404,'This building is unavailable')
    p=db.get(Property,key)
    if not p:
        register(db,city)
        p=db.get(Property,key)
    return {**view(db,p,u),'balance':balance(db,u.id,'xp')}

class Studio(Strict):
    name:str=Field(min_length=2,max_length=48)
    board:Literal['navy','forest','burgundy']
    description:str=Field(max_length=220,default='')
    access:Literal['private','friends','invite','public']='private'
    guests:list[UUID]=Field(default_factory=list,max_length=32)

@router.patch('/{key}/studio')
def publish(key:str,data:Studio,u=Depends(current_user),db=Depends(get_db)):
    import re,unicodedata
    p=locked_property(db,key)
    if p.owner!=u.id:
        raise HTTPException(403,'Only the owner can publish changes')
    name=unicodedata.normalize('NFKC',data.name).strip()
    if len(name)<2 or not re.fullmatch(r"[\w .’'&-]+",name) or re.search(r'\b(admin|moderator|mindaam support|fuck|shit)\b',name,re.I):
        raise HTTPException(422,'Choose a different property name')
    p.name=name
    p.style={'board':data.board,'description':data.description.strip(),'access':data.access,
             'guests':list(map(str,data.guests)) if data.access=='invite' else []}
    audit(db,u,'property.publish',key,{'generation':p.generation})
    return view(db,p,u)

def may_visit(db,p,u):
    from .world import friends
    if u.id==p.owner:
        return True
    if not p.owner or blocked(db,p.owner,u.id):
        return False
    access=p.style.get('access','private')
    return access=='public' or (access=='friends' and friends(db,p.owner,u.id)) or (
        access=='invite' and u.id in p.style.get('guests',[]))

@router.get('/admin/overview')
def overview(u=Depends(super_admin),db=Depends(get_db)):
    count=lambda c:db.scalar(select(func.count(c)))
    total=count(Property.id)
    owned=count(Property.owner)
    def volume(condition):
        return db.scalar(select(func.coalesce(func.sum(Trade.amount),0)).where(condition))
    return dict(registered=total,available=total-owned,owned=owned,owners=count(func.distinct(Property.owner)),
                claims_xp=volume(Trade.seller.is_(None)),resales_xp=volume(Trade.seller.is_not(None)),
                pending=db.scalar(select(func.count(Offer.id)).where(Offer.state.in_(['pending','countered']),Offer.expires>time.time())))
