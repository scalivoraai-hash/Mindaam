import uuid
from sqlalchemy import select
from backend.tests.test_core import system,register,onboard
from backend.api.models import User,Audit

def payload():return {'request_id':str(uuid.uuid4()),'category':'feature','title':'Longer walking trails','description':'Please add more accessible walking routes near the parks.'}
def test_feedback_auth_rate_limit_idempotency_and_private_review(system):
 c,sessions=system
 assert c.post('/api/feedback',json=payload()).status_code==401
 h,u=register(c);onboard(c,h);data=payload()
 r=c.post('/api/feedback',headers=h,json=data);assert r.status_code==201,r.text
 assert c.post('/api/feedback',headers=h,json=data).json()==r.json()
 assert c.get('/api/super-admin/feedback',headers=h).status_code==403
 assert c.patch('/api/super-admin/feedback/'+r.json()['id'],headers=h,json={'status':'completed','internal_notes':'secret review'}).status_code==403
 for _ in range(2):assert c.post('/api/feedback',headers=h,json=payload()).status_code==201
 assert c.post('/api/feedback',headers=h,json=payload()).status_code==429
 admin,owner=register(c,'owner')
 with sessions.begin() as db:db.get(User,owner['id']).role='super_admin'
 listing=c.get('/api/super-admin/feedback?category=feature&q=walking&limit=1',headers=admin)
 assert listing.status_code==200,listing.text
 assert listing.json()['total']==3 and len(listing.json()['items'])==1
 update=c.patch('/api/super-admin/feedback/'+r.json()['id'],headers=admin,json={'status':'reviewing','internal_notes':'Private owner review'})
 assert update.status_code==200,update.text
 replay=c.post('/api/feedback',headers=h,json=data)
 assert 'internal_notes' not in replay.json() and 'Private owner review' not in replay.text
 exported=c.get('/api/privacy/export',headers=h);assert exported.status_code==200
 assert len(exported.json()['feedback'])==3 and 'Private owner review' not in exported.text
 with sessions() as db:assert db.scalar(select(Audit).where(Audit.action=='feedback.reviewed')) is not None

def test_feedback_validation_and_cross_user_request_id(system):
 c,sessions=system;h,u=register(c);onboard(c,h);data=payload()
 assert c.post('/api/feedback',headers=h,json={**data,'title':'  '}).status_code==422
 assert c.post('/api/feedback',headers=h,json={**data,'description':'x'*4001}).status_code==422
 assert c.post('/api/feedback',headers=h,json=data).status_code==201
 other,v=register(c,'other')
 assert c.post('/api/feedback',headers=other,json=data).status_code==409
