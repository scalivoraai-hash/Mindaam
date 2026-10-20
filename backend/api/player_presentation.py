"""Read-only presentation of authoritative rentals and transit on the existing socket."""
import time
from types import SimpleNamespace
from sqlalchemy import select
from . import mobility, transit


def transport_states(db, city, now):
    rentals={lease.user_id:(lease,asset) for lease,asset in db.execute(
        select(mobility.RentalLease,mobility.RentalAsset).join(mobility.RentalAsset,
        mobility.RentalAsset.id==mobility.RentalLease.asset_id).where(
        mobility.RentalAsset.city==city,mobility.RentalLease.ended_at==None,mobility.RentalLease.expires_at>now))}
    passengers={}
    for ticket,vehicle,route in db.execute(select(transit.Ticket,transit.Vehicle,transit.Route)
        .join(transit.Vehicle,transit.Vehicle.id==transit.Ticket.vehicle_id)
        .join(transit.Route,transit.Route.id==transit.Vehicle.route_id)
        .where(transit.Ticket.state=='aboard', (transit.Route.origin==city)|(transit.Route.destination==city))):
        position=transit.position(route,vehicle,now)
        if position['road_city']==city and not position['compressed']:
            passengers[ticket.user_id]=(ticket,position,route)
    return rentals,passengers


def presentation(p, rentals, passengers, now):
    vehicle=None
    point=SimpleNamespace(x=p.x,z=p.z,city=p.city,zone_id=p.zone_id)
    y=0;seated=False
    if p.user_id in passengers and p.zone_id.startswith('bus:'):
        ticket,position,route=passengers[p.user_id]
        seat=transit.passenger_position({'position':position},ticket.seat)
        point.x,point.z=seat['x'],seat['z'];point.city=position['road_city'];y=seat['y'];seated=ticket.seat is not None
        vehicle={'id':ticket.vehicle_id,'kind':'bus','seat':ticket.seat,'number':route.number,
            'destination':route.destination,**position,'sampled_at':now}
    elif p.user_id in rentals and p.zone_id=='world':
        lease,asset=rentals[p.user_id]
        vehicle={'id':asset.id,'kind':asset.kind,'x':p.x,'z':p.z,'heading':lease.heading,
            'speed':lease.speed if now-lease.last_update<.6 else 0,'seat':'driver','sampled_at':now}
    speed=p.motion_speed if now-p.last_move<.6 and not vehicle else 0
    state=('ON_BUS' if vehicle and vehicle['kind']=='bus' else 'IN_CAR' if vehicle and vehicle['kind']=='car'
        else 'ON_BIKE' if vehicle and vehicle['kind'] in ['bike','ebike','scooter']
        else 'IN_VEHICLE' if vehicle else 'IN_EVENT' if p.zone_id.startswith('event:')
        else 'RUNNING' if speed>.1 and p.mode=='run' else 'WALKING' if speed>.1 else 'IDLE')
    return point,{'x':point.x,'z':point.z,'y':y,'seated':seated,'vehicle':vehicle,
        'movement_state':state,'speed':speed,'last_move':p.last_move,'sampled_at':now}
