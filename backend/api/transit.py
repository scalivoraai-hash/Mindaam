"""Scheduled virtual transit. Routes, seats, tickets and fares share the existing DB."""
import time,math
from functools import lru_cache
from uuid import UUID
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import String,Integer,Float,Boolean,ForeignKey,UniqueConstraint,select,func
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base,get_db
from .models import User,Presence,Session,Audit,uid
from .auth import current_user,display_profile
from .core import Strict,serialize
from .economy import credit,balance
from .mobility_payments import charge
from .geography import district,safe_spawn,driving_segments,traversable
from .growth import require_access,access
router=APIRouter(prefix='/api/transit')

class Route(Base):
 __tablename__='transport_routes'
 id:Mapped[str]=mapped_column(String(100),primary_key=True)
 origin:Mapped[str]=mapped_column(String(50),index=True)
 destination:Mapped[str]=mapped_column(String(50))
 number:Mapped[str]=mapped_column(String(12))
 frequency:Mapped[int]=mapped_column(Integer,default=600)
 duration:Mapped[int]=mapped_column(Integer,default=150)
 fare:Mapped[int]=mapped_column(Integer,default=20)
 capacity:Mapped[int]=mapped_column(Integer,default=40)
 enabled:Mapped[bool]=mapped_column(Boolean,default=True)
class Stop(Base):
 __tablename__='transport_stops'
 id:Mapped[str]=mapped_column(String(100),primary_key=True)
 city:Mapped[str]=mapped_column(String(50),index=True)
 name:Mapped[str]=mapped_column(String(120))
 x:Mapped[float]=mapped_column(Float)
 z:Mapped[float]=mapped_column(Float)
 offset:Mapped[int]=mapped_column(Integer,default=0)
 enabled:Mapped[bool]=mapped_column(Boolean,default=True)
class Vehicle(Base):
 __tablename__='transport_vehicle_instances'
 id:Mapped[str]=mapped_column(String(150),primary_key=True)
 route_id:Mapped[str]=mapped_column(ForeignKey('transport_routes.id'),index=True)
 departure:Mapped[float]=mapped_column(Float)
 capacity:Mapped[int]=mapped_column(Integer)
 duration:Mapped[int]=mapped_column(Integer)
 fare:Mapped[int]=mapped_column(Integer)
class Hail(Base):
 __tablename__='transport_hails'
 vehicle_id:Mapped[str]=mapped_column(ForeignKey('transport_vehicle_instances.id'),primary_key=True)
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
 stop_id:Mapped[str]=mapped_column(String(100),default='')
 created_at:Mapped[float]=mapped_column(Float,default=time.time)
class Ticket(Base):
 __tablename__='transport_tickets'
 id:Mapped[str]=mapped_column(String(36),primary_key=True)
 user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
 vehicle_id:Mapped[str]=mapped_column(ForeignKey('transport_vehicle_instances.id'),index=True)
 fare:Mapped[int]=mapped_column(Integer)
 state:Mapped[str]=mapped_column(String(20),default='aboard')
 seat:Mapped[int|None]=mapped_column(Integer,nullable=True)
 stop_requested:Mapped[bool]=mapped_column(Boolean,default=False)
 created_at:Mapped[float]=mapped_column(Float,default=time.time)
 exited_at:Mapped[float|None]=mapped_column(Float,nullable=True)
 __table_args__=(UniqueConstraint('user_id','vehicle_id'),UniqueConstraint('vehicle_id','seat'))

@lru_cache(maxsize=64)
def hub(city):
 """Use a licensed driving segment with space along its centre line. No invented road."""
 spawn=safe_spawn(city);segments=sorted(driving_segments(city),key=lambda ab:math.hypot((ab[0][0]+ab[1][0])/2-spawn[0],(ab[0][1]+ab[1][1])/2-spawn[1]))
 for a,b in segments:
  length=math.dist(a,b)
  if length<16:continue
  points=[[a[0]+(b[0]-a[0])*i/20,a[1]+(b[1]-a[1])*i/20] for i in range(21)]
  if all(traversable(city,*p,'car') for p in points):
   centre=points[10];nx,nz=-(b[1]-a[1])/length,(b[0]-a[0])/length
   stop=next(([centre[0]+nx*d,centre[1]+nz*d] for d in [4.5,-4.5,3,-3] if traversable(city,centre[0]+nx*d,centre[1]+nz*d)),centre)
   return {'city':city,'x':stop[0],'z':stop[1],'road':points,'heading':math.atan2(b[0]-a[0],b[1]-a[1])}
 raise HTTPException(409,'This destination needs an approved bus approach road')

def seed_network(db):
 from .discovery import catalog
 cities=[c for c in catalog(db) if c['enabled'] and c.get('public',True) and c.get('joinable',True) and c.get('transport_enabled',True)]
 countries={c['country'] for c in cities}
 for c in cities:
  h=hub(c['id']);road=h['road'];sx,sz=road[5]
  for suffix,name,x,z,offset in [('central',c['name']+' Central',h['x'],h['z'],0),('local',c['name']+' Bus Stop',sx,sz,-30)]:
   id=c['id']+':'+suffix
   if not db.get(Stop,id):db.add(Stop(id=id,city=c['id'],name=name,x=x,z=z,offset=offset))
 for country in countries:
  members=sorted([c for c in cities if c['country']==country],key=lambda c:(c['id']!='london',c['id']))
  if len(members)<2:continue
  centre=members[0]['id']
  for i,c in enumerate(members[1:]):
   for origin,destination in [(centre,c['id']),(c['id'],centre)]:
    id=f'{origin}--{destination}'
    if not db.get(Route,id):db.add(Route(id=id,origin=origin,destination=destination,number=str(101+i),fare=20,frequency=600,duration=150,capacity=40))
 db.flush()

def slot(r,now):
 offset=(int(r.number)-101)*30%r.frequency
 start=math.floor((now-offset)/r.frequency)*r.frequency+offset
 return start if now<=start+30 else start+r.frequency

def vehicle(db,r,start):
 id=f'{r.id}:{int(start)}';v=db.scalar(select(Vehicle).where(Vehicle.id==id).with_for_update())
 if not v:v=Vehicle(id=id,route_id=r.id,departure=start,capacity=r.capacity,duration=r.duration,fare=r.fare);db.add(v);db.flush()
 return v

def real_passengers(db,id):
 alive=select(Session.user_id).where(Session.expires_at>time.time())
 return list(db.scalars(select(Ticket).join(Presence,Presence.user_id==Ticket.user_id).join(User,User.id==Ticket.user_id).where(Ticket.vehicle_id==id,Ticket.state=='aboard',Presence.zone_id=='bus:'+id,Presence.updated_at>time.time()-45,User.suspended==False,User.id.in_(alive))))

def bus_fraction(now,start,road_length=100):
 # Accelerated approach/departure on approved road geometry; timetable is server-owned.
 speed=46.0;delta=now-start;rate=speed/max(1,road_length)
 if delta<-30:return max(0,min(.25,.25+(delta+30)*rate))
 if delta<-15:return .25
 if delta<0:return max(.25,min(.5,.5+delta*rate))
 if delta<=30:return .5
 return min(1,.5+(delta-30)*rate)

def position(r,v,now):
 elapsed=now-v.departure-30;progress=max(0,min(1,elapsed/v.duration));arriving=elapsed>=v.duration-30
 road_city=r.destination if arriving else r.origin;h=hub(road_city)
 road=h['road'];length=math.dist(road[0],road[-1]);fraction=max(0,min(.5,.5+(elapsed-v.duration)*46/max(1,length))) if arriving else bus_fraction(now,v.departure,length);index=min(19,int(fraction*20));t=fraction*20-index
 a,b=road[index],road[index+1]
 delta=now-v.departure;stopped=(-30<=delta<=-15 or 0<=delta<=30 or progress>=1)
 return {'x':a[0]+(b[0]-a[0])*t,'z':a[1]+(b[1]-a[1])*t,'heading':h['heading'],'road_city':road_city,'progress':progress,'stopped':stopped,'stage':'Arrived' if progress>=1 else 'Boarding' if stopped else 'Arrival approach' if arriving else 'Leaving the hub' if elapsed<=30 else 'Compressed intercity journey','remaining':max(0,round(v.departure+30+v.duration-now)),'virtual_cruise_speed':46,'compressed':30<elapsed<v.duration-30}

def stops(db,city):
 rows=[serialize(s) for s in db.scalars(select(Stop).where(Stop.city==city,Stop.enabled==True))]
 return rows or [{'id':city+':central','name':city+' Central','city':city,'offset':0,'x':hub(city)['x'],'z':hub(city)['z']}]
def boarding_stop(db,u,city):
 p=db.get(Presence,u.id);rows=stops(db,city)
 return min(rows,key=lambda s:math.hypot(s['x']-(p.x if p else 0),s['z']-(p.z if p else 0)))

def passenger_position(journey,seat):
 base=journey['position'];heading=base['heading'];n=max(0,(seat or 1)-1);side=(-.65 if n%2==0 else .65) if seat else 0;row=(n//2)%10;forward=-2.5+row*.55 if seat else 2.5
 return {'x':base['x']+side*math.cos(heading)+forward*math.sin(heading),'z':base['z']-side*math.sin(heading)+forward*math.cos(heading),'y':.95+(2.5 if n>=20 else 0)}

def current(db,u):return db.scalar(select(Ticket).where(Ticket.user_id==u.id,Ticket.state=='aboard').order_by(Ticket.created_at.desc()).limit(1))

def journey(db,u):
 t=current(db,u)
 if not t:return None
 v=db.get(Vehicle,t.vehicle_id);r=db.get(Route,v.route_id);pos=position(r,v,time.time());passengers=real_passengers(db,v.id)
 from .world import blocked,friends
 return {'ticket_id':t.id,'vehicle_id':v.id,'route':serialize(r),'position':pos,'arrived':pos['progress']>=1,'seat':t.seat,'capacity':v.capacity,'stop_requested':t.stop_requested,'passenger_count':len(passengers),'seats':[p.seat for p in passengers if p.seat is not None],'passengers':[{'id':p.id,'username':p.username,'avatar':p.avatar,'is_self':p.id==u.id,'seat':a.seat,'friend':friends(db,u.id,p.id),**display_profile(p)} for a in passengers if (p:=db.get(User,a.user_id)) and not blocked(db,u.id,p.id) and (p.id==u.id or p.privacy not in ['Ghost Mode','Event Mode'] and (p.privacy!='Friends Only' or friends(db,u.id,p.id)))]}

@router.get('/board/{city}')
def board(city:str,u=Depends(current_user),db=Depends(get_db)):
 from .discovery import cities
 catalog={c['id']:c for c in cities(db)}
 if city not in catalog or not catalog[city]['enabled']:raise HTTPException(404,'World unavailable')
 now=time.time();rows=[];vehicles=[]
 for r in db.scalars(select(Route).where(Route.origin==city,Route.enabled==True)):
  if r.destination not in catalog or not all(catalog[r.destination].get(k,True) for k in ['enabled','public','joinable','transport_enabled']):continue
  start=slot(r,now);id=f'{r.id}:{int(start)}';n=len(real_passengers(db,id));instance=db.get(Vehicle,id);fare=instance.fare if instance else r.fare;capacity=instance.capacity if instance else r.capacity;h=hub(city);stop=boarding_stop(db,u,city);arrival=start+stop['offset'];boarding_end=arrival+(15 if stop['offset'] else 30)
  last=start if start-now<60 else start-r.frequency
  if -60<now-last<65:
   road=h['road'];fraction=bus_fraction(now,last,math.dist(road[0],road[-1]));idx=min(19,int(fraction*20));factor=fraction*20-idx;a,b=road[idx],road[idx+1]
   if fraction<1:vehicles.append({'id':f'{r.id}:{int(last)}','number':r.number,'destination_name':catalog[r.destination]['name'],'position':{'x':a[0]+(b[0]-a[0])*factor,'z':a[1]+(b[1]-a[1])*factor,'heading':h['heading']}})
  rows.append({**serialize(r),'fare':fare,'currency':'xp','capacity':capacity,'destination_name':catalog[r.destination]['name'],'vehicle_id':id,'stop_id':stop['id'],'stop_name':stop['name'],'arrival_at':arrival,'following_at':arrival+r.frequency,'boarding_until':boarding_end,'passengers':n,'full':n>=capacity,'state':'BOARDING' if arrival<=now<=boarding_end else 'APPROACHING' if 0<arrival-now<60 else 'SCHEDULED','position':h,'locked':not bool(access(db,u,r.destination))})
 return {'server_time':now,'hub':{**hub(city),'name':catalog[city]['name']+' Central'},'stops':stops(db,city),'routes':rows,'vehicles':vehicles,'journey':journey(db,u),'balance':balance(db,u.id,'xp'),'currency':'xp','network_note':'Travel via the country interchange when there is no direct route.'}

class VehicleInput(Strict):
 vehicle_id:str=Field(max_length=150)
class BoardInput(VehicleInput):
 id:UUID
 expected_fare:int|None=Field(default=None,ge=0,le=1000)
 expected_currency:Literal['xp','credits']|None=None

def boarding(db,u,id,hail=False):
 try:rid,start=id.rsplit(':',1);start=int(start)
 except (ValueError,TypeError):raise HTTPException(422,'Invalid vehicle')
 r=db.scalar(select(Route).where(Route.id==rid).with_for_update())
 if not r or not r.enabled:raise HTTPException(404,'Route unavailable')
 from .discovery import catalog
 available={c['id'] for c in catalog(db) if all(c.get(k,True) for k in ['enabled','public','joinable','transport_enabled'])}
 if r.origin not in available or r.destination not in available:raise HTTPException(409,'Route suspended')
 now=time.time()
 stop=boarding_stop(db,u,r.origin);arrival=start+stop['offset'];end=arrival+(15 if stop['offset'] else 30)
 if start!=slot(r,now) or now<arrival-(60 if hail else 0) or now>end:raise HTTPException(409,'This bus is not accepting passengers yet. Check the departure board.')
 p=db.get(Presence,u.id);h=stop
 from .mobility import current as rental_current
 if rental_current(db,u):raise HTTPException(409,'Exit your rental before boarding transit')
 if not p or p.city!=r.origin or p.zone_id!='world' or math.hypot(p.x-h['x'],p.z-h['z'])>12:raise HTTPException(409,'Walk to this bus stop first')
 return r,vehicle(db,r,start),p

@router.post('/hail')
def hail(data:VehicleInput,u=Depends(current_user),db=Depends(get_db)):
 r,v,p=boarding(db,u,data.vehicle_id,True)
 if len(real_passengers(db,v.id))>=v.capacity:raise HTTPException(409,'Bus full. Take the following departure.')
 if not db.get(Hail,(v.id,u.id)):db.add(Hail(vehicle_id=v.id,user_id=u.id,stop_id=boarding_stop(db,u,r.origin)['id']))
 return {'ok':True,'message':'Hand raised. This bus will stop at your hub.'}

@router.post('/board')
def buy(data:BoardInput,u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update())
 prior=db.get(Ticket,str(data.id))
 if prior:
  if prior.user_id!=u.id or prior.vehicle_id!=data.vehicle_id:raise HTTPException(409,'Ticket ID already used')
  return {'ticket':serialize(prior),'journey':journey(db,u),'balance':balance(db,u.id,'xp'),'currency':'xp','duplicate':True}
 previous=db.scalar(select(Ticket).where(Ticket.user_id==u.id,Ticket.vehicle_id==data.vehicle_id))
 if previous:return {'ticket':serialize(previous),'journey':journey(db,u),'balance':balance(db,u.id,'xp'),'currency':'xp','duplicate':True}
 if current(db,u):raise HTTPException(409,'Leave your current journey before boarding another')
 r,v,p=boarding(db,u,data.vehicle_id)
 require_access(db,u,r.destination)
 if not db.get(Hail,(v.id,u.id)):raise HTTPException(409,'Hail this bus before boarding')
 active=real_passengers(db,v.id)
 if len(active)>=v.capacity:raise HTTPException(409,'Bus full. Take the following departure.')
 if data.expected_fare!=v.fare:raise HTTPException(409,{'code':'FARE_CHANGED','message':'Review the latest fare and confirm your ticket again.'})
 charge(db,u.id,'bus',v.fare,v.id,'transport:'+str(data.id),data.expected_currency)
 occupied=set(db.scalars(select(Ticket.seat).where(Ticket.vehicle_id==v.id,Ticket.seat!=None)))
 assigned=next((n for n in range(1,v.capacity+1) if n not in occupied),None)
 t=Ticket(id=str(data.id),user_id=u.id,vehicle_id=v.id,fare=v.fare,seat=assigned);db.add(t);p.zone_id='bus:'+v.id;p.mode='bus';p.updated_at=time.time();p.last_move=p.updated_at;p.motion_speed=0;db.flush()
 ride=journey(db,u);point=passenger_position(ride,t.seat);p.x,p.z=point['x'],point['z']
 db.add(Audit(actor_id=u.id,action='transport.board',target=v.id,details={'ticket_id':t.id,'fare':v.fare,'currency':'xp'}))
 return {'ticket':serialize(t),'journey':ride,'position':{**point,'mode':'bus','zone_id':p.zone_id,'last_move':p.last_move},'balance':balance(db,u.id,'xp'),'currency':'xp','duplicate':False}
class Seat(Strict):
 seat:int=Field(ge=1,le=40)
@router.post('/seat')
def seat(data:Seat,u=Depends(current_user),db=Depends(get_db)):
 t=current(db,u)
 if not t:raise HTTPException(409,'Board a bus first')
 v=db.scalar(select(Vehicle).where(Vehicle.id==t.vehicle_id).with_for_update())
 if data.seat>v.capacity:raise HTTPException(422,'Seat unavailable')
 other=db.scalar(select(Ticket).where(Ticket.vehicle_id==v.id,Ticket.seat==data.seat,Ticket.id!=t.id))
 if other:raise HTTPException(409,'Someone is already in this seat')
 t.seat=data.seat;db.flush();return journey(db,u)
@router.post('/request-stop')
def request_stop(u=Depends(current_user),db=Depends(get_db)):
 t=current(db,u)
 if not t:raise HTTPException(409,'Board a bus first')
 t.stop_requested=True;return {'ok':True}
@router.post('/exit')
def exit_bus(u=Depends(current_user),db=Depends(get_db)):
 db.scalar(select(User.id).where(User.id==u.id).with_for_update());t=current(db,u)
 if not t:raise HTTPException(409,'No active journey')
 v=db.get(Vehicle,t.vehicle_id);r=db.get(Route,v.route_id);now=time.time()
 if not position(r,v,now)['stopped']:raise HTTPException(409,'Wait until the bus stops')
 destination=r.origin if now<=v.departure+30 else r.destination
 # Permanent access was checked at purchase; an admin-disabled world returns to origin safely.
 from .discovery import catalog
 available={c['id'] for c in catalog(db) if c.get('enabled') and c.get('joinable',True)}
 if destination not in available:destination=r.origin
 p=db.get(Presence,u.id)
 if not p:p=Presence(user_id=u.id,city=destination);db.add(p)
 h=hub(destination)
 if destination==r.origin and now<v.departure:
  local=next((s for s in stops(db,destination) if s['offset']==-30),None)
  if local:h=local
 p.city=destination;p.x=h['x'];p.z=h['z'];p.zone_id='world';p.mode='walk';p.last_move=now;p.updated_at=now;u.city=destination
 t.state='exited';t.seat=None;t.exited_at=now
 db.add(Audit(actor_id=u.id,action='transport.exit',target=v.id));db.flush()
 return {'city':destination,'position':{'x':p.x,'z':p.z}}

def maintenance(db):
 for t in db.scalars(select(Ticket).where(Ticket.state=='aboard')):
  v=db.get(Vehicle,t.vehicle_id);p=db.get(Presence,t.user_id)
  if not p or p.updated_at<time.time()-45:
   t.seat=None
  if time.time()>v.departure+30+v.duration+900:
   u=db.get(User,t.user_id)
   if u:exit_bus(u,db)
