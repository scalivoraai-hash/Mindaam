import hashlib,time,json
import pytest
from sqlalchemy import event,delete
from fastapi import HTTPException
from backend.tests.test_core import system,register,onboard
from backend.api import main,realtime_cache,media
from backend.api.models import Config,User,Presence,Session,Social
from backend.api.media_policy import Policy


def test_capacity_policy_rejects_untested_large_events_and_non_owner_updates(system):
    c,dbs=system;h,u=register(c,'capacity_owner');onboard(c,h)
    body={'title':'Local capacity test','city':'manchester','starts_at':time.time()+60,'event_type':'Public Talk','capacity':101}
    assert c.post('/api/events',headers=h,json=body).status_code==422
    assert c.put('/api/super-admin/media-policy',headers=h,json={}).status_code==403
    with dbs.begin() as db:db.get(User,u['id']).role='super_admin'
    assert c.put('/api/super-admin/media-policy',headers=h,json={'event_capacity_limit':250}).status_code==422
    assert c.put('/api/super-admin/media-policy',headers=h,json={'auto_subscribe':True}).status_code==422
    assert c.put('/api/super-admin/media-policy',headers=h,json={'event_capacity_limit':50}).status_code==200
    body.pop('capacity');r=c.post('/api/events',headers=h,json=body);assert r.status_code==201,r.text
    assert r.json()['capacity']==50


def test_stage_host_plus_three_and_demotion_stops_publication(system,monkeypatch):
    c,dbs=system;users=[register(c,'stage_'+str(i)) for i in range(5)]
    for h,_ in users:onboard(c,h)
    host=users[0];e=c.post('/api/events',headers=host[0],json={'title':'Local stage test','city':'manchester','starts_at':time.time()+60,'event_type':'Public Talk','venue_experience_type':'auditorium','venue_mode':'grand_arena','communication_mode':'liveface'}).json()
    assert c.post('/api/growth/worlds/manchester/starter',headers=host[0],json={'confirmed':True}).status_code==200
    from backend.api.economy import credit
    import uuid
    with dbs.begin() as db:credit(db,host[1]['id'],100,'purchase','fixture','stage-cost-booking')
    reserved=c.post('/api/events/'+e['id']+'/venue/booking',headers=host[0],json={'request_id':str(uuid.uuid4()),'hours':1,'expected_cost':100,'starts_at':time.time()-1})
    assert reserved.status_code==200,reserved.text
    for h,_ in users[1:]:assert c.post('/api/events/'+e['id']+'/join',headers=h).status_code==200
    assert c.post('/api/events/'+e['id']+'/state/start',headers=host[0]).status_code==200
    async def permission(*args):pass
    monkeypatch.setattr(media,'update_participant_permission',permission)
    for _,u in users[1:4]:assert c.post(f'/api/events/{e["id"]}/people/{u["id"]}/speaker',headers=host[0]).status_code==200
    assert c.post(f'/api/events/{e["id"]}/people/{users[4][1]["id"]}/speaker',headers=host[0]).status_code==409
    # Changing an existing speaker to cohost consumes no additional publisher slot.
    assert c.post(f'/api/events/{e["id"]}/people/{users[1][1]["id"]}/cohost',headers=host[0]).status_code==200
    assert c.post(f'/api/events/{e["id"]}/people/{users[1][1]["id"]}/audience',headers=host[0]).status_code==200
    assert c.post(f'/api/events/{e["id"]}/people/{users[4][1]["id"]}/speaker',headers=host[0]).status_code==200


def test_cache_measures_idle_queries_and_invalidates_committed_motion_privacy_logout(system,monkeypatch,tmp_path):
    c,dbs=system;h,u=register(c,'cached_one');onboard(c,h)
    h2,u2=register(c,'cached_two');onboard(c,h2)
    monkeypatch.setattr(realtime_cache,'_redis',None)
    token=h['Authorization'][7:];build=lambda:main.realtime_state(token,with_expiry=True)
    counts={'sql':0}
    def count(*_):counts['sql']+=1
    engine=dbs.kw['bind'];event.listen(engine,'before_cursor_execute',count)
    try:
        for _ in range(20):build()
        baseline=counts['sql'];counts['sql']=0;cache=realtime_cache.StateCache(allow_local=True)
        for tick in range(20):state=cache.read(build,now=tick*.5)
        optimized=counts['sql']
        evidence={'samples':20,'baseline_sql':baseline,'cached_sql':optimized,'reduction_pct':round((1-optimized/baseline)*100,1),'hits':cache.hits,'misses':cache.misses,'scope':'idle local two-user fixture; not moving-world or GCP capacity evidence'}
        print('SNAPSHOT_MEASUREMENT '+json.dumps(evidence))
        assert optimized<baseline*.4,evidence
        with dbs.begin() as db:db.get(Presence,u2['id']).x+=1
        misses=cache.misses;cache.read(build,now=9.6);assert cache.misses==misses+1
        with dbs.begin() as db:db.get(User,u2['id']).privacy='Ghost Mode'
        assert all(p['id']!=u2['id'] for p in cache.read(build,now=9.7)['players'])
        with dbs.begin() as db:db.execute(delete(Session).where(Session.user_id==u['id']))
        with pytest.raises(HTTPException):cache.read(build,now=9.8)
    finally:event.remove(engine,'before_cursor_execute',count)


def test_cache_rollback_and_expiry_are_safe(system,monkeypatch):
    c,dbs=system;h,u=register(c,'expiry_cache');onboard(c,h);monkeypatch.setattr(realtime_cache,'_redis',None)
    token=h['Authorization'][7:];cache=realtime_cache.StateCache(allow_local=True);build=lambda:main.realtime_state(token,with_expiry=True)
    cache.read(build,now=0);before=realtime_cache.revision()
    with dbs() as db:
        db.get(User,u['id']).suspended=True;db.flush();db.rollback()
    assert realtime_cache.revision()==before
    # A cached authentication expiry cannot be extended by the snapshot TTL.
    cache.expires_at=time.time()-1;cache.read(build,now=.1);assert cache.misses==2
