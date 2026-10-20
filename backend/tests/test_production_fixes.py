import time
import asyncio,threading,time
from backend.tests.test_core import system,register,onboard
from backend.api import main

def test_realtime_database_work_never_runs_on_event_loop(monkeypatch):
 loop_thread=threading.get_ident();seen=[]
 def state(token,with_expiry=False):
  seen.append(threading.get_ident());value={'type':'state'}
  return (value,time.time()+60) if with_expiry else value
 class Socket:
  cookies={}
  headers={}
  async def accept(self):pass
  async def receive_json(self):return {'token':'testing'}
  async def send_json(self,result):raise main.WebSocketDisconnect()
 monkeypatch.setattr(main,'realtime_state',state)
 asyncio.run(main.realtime(Socket()))
 assert seen and seen[0]!=loop_thread

def test_inventory_claim_replay_and_rankings(system):
 c,_=system;h,u=register(c,'baskettest');onboard(c,h)
 before=c.get('/api/inventory',headers=h).json();assert before['total']==0
 r=c.post('/api/collectibles/london-local-0/claim',headers=h,json={});assert r.status_code==200,r.text
 first=c.get('/api/inventory',headers=h).json();assert first['total']==1 and first['xp']==5
 c.post('/api/collectibles/london-local-0/claim',headers=h,json={})
 assert c.get('/api/inventory',headers=h).json()==first
 for scope in ['local','city','uk']:
  rows=c.get('/api/rankings?city=london&scope='+scope,headers=h).json()['rows'];assert rows[0]['id']==u['id'] and rows[0]['score']==5
 assert c.get('/api/inventory').status_code==401
 assert c.get('/api/rankings?scope=wrong',headers=h).status_code==422

def test_fast_travel_validates_destination_cooldown_and_inventory(system):
 c,_=system;h,u=register(c,'traveller');onboard(c,h)
 assert c.post('/api/growth/worlds/milton-keynes/starter',headers=h,json={'confirmed':True}).status_code==200
 data=c.get('/api/places/milton-keynes',headers=h).json();p=data['places'][0]
 assert c.post('/api/places/travel/visit',headers=h,json={'city':'milton-keynes','place_id':'invented'}).status_code==404
 r=c.post('/api/places/travel/visit',headers=h,json={'city':'milton-keynes','place_id':p['id']});assert r.status_code==200,r.text
 assert r.json()['city']=='milton-keynes'
 assert c.get('/api/inventory',headers=h).json()['total']==0
 assert c.post('/api/places/travel/visit',headers=h,json={'city':'milton-keynes','place_id':p['id']}).status_code==429

def test_health_requires_database(monkeypatch):
 class Down:
  def connect(self):raise RuntimeError('down')
 monkeypatch.setattr(main,'engine',Down())
 from fastapi import HTTPException
 import pytest
 with pytest.raises(HTTPException) as err:main.ready()
 assert err.value.status_code==503
