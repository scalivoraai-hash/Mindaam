"""Keep authoritative per-input checks inside the existing freshness budget."""
import hashlib
import threading
import time
import pytest
from fastapi import HTTPException
from sqlalchemy import event
from backend.tests.test_core import system,register,onboard
from backend.api import main,movement_policy
from backend.api.models import Config,Presence,Session,User
from backend.api.growth import WorldAccess
from backend.api.expansion import Destination

def setup_motion(system):
    client,sessions=system
    headers,user=register(client,'query_budget');onboard(client,headers)
    token=headers['Authorization'][7:]
    with sessions.begin() as db:
        if not db.get(Config,movement_policy.KEY):
            db.add(Config(key=movement_policy.KEY,value=movement_policy.initial(db)))
        p=db.get(Presence,user['id']);p.x=p.z=0;p.last_move=time.time()-.12
    data=main.MotionInput(type='input',seq=1,city='london',zone='world',action='move',x=1,z=0)
    return sessions,token,user,data

def test_fresh_motion_checks_use_three_reads_even_with_database_latency(system):
    sessions,token,user,data=setup_motion(system)
    engine=sessions.kw['bind'];thread=threading.get_ident();reads=[]
    def latency(conn,cursor,statement,parameters,context,executemany):
        if threading.get_ident()==thread and statement.lstrip().upper().startswith('SELECT'):
            reads.append(statement);time.sleep(.06)
    event.listen(engine,'before_cursor_execute',latency)
    try:
        data._received=(time.time(),time.monotonic())
        result=main.realtime_motion(token,data)
    finally:event.remove(engine,'before_cursor_execute',latency)
    assert len(reads)==3,reads
    assert result['position']['x']>0
    assert result['position']['speed']>0

@pytest.mark.parametrize('change,status',[('session',401),('suspended',403),('world_access',403),('closed_city',403)])
def test_batched_reads_revalidate_revocations_each_input(system,change,status):
    sessions,token,user,data=setup_motion(system)
    assert main.realtime_motion(token,data)['type']=='motion'
    with sessions.begin() as db:
        if change=='session':db.get(Session,hashlib.sha256(token.encode()).hexdigest()).expires_at=0
        elif change=='suspended':db.get(User,user['id']).suspended=True
        elif change=='world_access':db.delete(db.get(WorldAccess,(user['id'],'london')))
        else:db.get(Destination,'london').joinable=False
    with pytest.raises(HTTPException) as error:main.realtime_motion(token,data)
    assert error.value.status_code==status

def test_batched_configuration_is_fresh_each_input(system):
    sessions,token,user,data=setup_motion(system)
    first=main.realtime_motion(token,data)
    with sessions.begin() as db:
        row=db.get(Config,movement_policy.KEY)
        row.value={**row.value,'version':row.value['version']+1,'speeds':{**row.value['speeds'],'walk':3}}
    second=main.realtime_motion(token,data)
    assert second['position']['movement_config']['version']==first['position']['movement_config']['version']+1
    assert second['position']['movement_config']['speeds']['walk']==3
