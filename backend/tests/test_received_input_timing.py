"""Database queue time cannot turn a short input into extra travel."""
import time
from types import SimpleNamespace
import pytest
from backend.tests.test_core import system,register,onboard
from backend.api import world,main
from backend.api.models import User,Presence
from backend.api.movement_policy import public

@pytest.mark.parametrize('processing_delay',[.02,.25,.34])
def test_queued_second_input_integrates_receipt_interval(system,monkeypatch,processing_delay):
    client,sessions=system
    headers,user=register(client,'receipt_interval');onboard(client,headers)
    wall=time.time();mono=time.monotonic()
    monkeypatch.setattr(world,'time',SimpleNamespace(time=lambda:wall+processing_delay,monotonic=lambda:mono+processing_delay))
    with sessions.begin() as db:
        u=db.get(User,user['id']);p=db.get(Presence,u.id)
        p.x=p.z=0;p.last_move=wall-.018;p.motion_speed=public(db)['speeds']['walk']
        step=world.move_locked(world.Movement(dx=1,dz=0),u,db,p,input_received=(wall,mono))
        assert step['x']==pytest.approx(public(db)['speeds']['walk']*.018,abs=1e-6)
        assert step['last_move']==wall
        assert p.updated_at==wall+processing_delay

@pytest.mark.parametrize('direction',[0,1])
def test_input_expiring_during_database_work_stops_without_travel(system,monkeypatch,direction):
    client,sessions=system
    headers,user=register(client,'expired_in_db');onboard(client,headers)
    wall=time.time();mono=time.monotonic()
    monkeypatch.setattr(world,'time',SimpleNamespace(time=lambda:wall+6,monotonic=lambda:mono+6))
    with sessions.begin() as db:
        u=db.get(User,user['id']);p=db.get(Presence,u.id)
        p.x=p.z=0;p.last_move=wall-.12;p.motion_speed=2
        step=world.move_locked(world.Movement(dx=direction,dz=0),u,db,p,input_received=(wall,mono))
        assert step['x']==step['z']==step['speed']==p.motion_speed==0
        assert p.updated_at==wall+6

def test_input_older_than_committed_movement_cannot_rewind_clock(system,monkeypatch):
    client,sessions=system
    headers,user=register(client,'old_receipt');onboard(client,headers)
    wall=time.time();mono=time.monotonic()
    monkeypatch.setattr(world,'time',SimpleNamespace(time=lambda:wall+.1,monotonic=lambda:mono+.1))
    with sessions.begin() as db:
        u=db.get(User,user['id']);p=db.get(Presence,u.id)
        p.x=p.z=0;p.last_move=wall+.05;p.motion_speed=2
        step=world.move_locked(world.Movement(dx=1,dz=0),u,db,p,input_received=(wall,mono))
        assert step['x']==step['speed']==0
        assert p.last_move==wall+.05

def test_receipt_clock_is_not_client_controlled():
    from pydantic import ValidationError
    value=dict(type='input',seq=1,city='london',zone='world',action='move',x=1,z=0)
    assert main.MotionInput.model_validate(value)._received is None
    with pytest.raises(ValidationError):main.MotionInput.model_validate({**value,'_received':[1,2]})
