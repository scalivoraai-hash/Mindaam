import time,uuid
from backend.tests.test_core import system,register,onboard
from backend.api.models import Event

def test_arena_is_closed_even_with_payment_actions_enabled(system,monkeypatch):
 monkeypatch.delenv('MINDAAM_GRAND_ARENA_ENABLED',raising=False)
 monkeypatch.setenv('MINDAAM_PAYMENT_ACTIONS_ENABLED','true')
 c,sessions=system;h,u=register(c);onboard(c,h)
 payload={'title':'Closed arena','city':'london','starts_at':time.time(),'venue_mode':'grand_arena'}
 r=c.post('/api/events',headers=h,json=payload);assert r.status_code==409 and 'Coming Soon' in r.text
 for mode in ['standard','virtual_auditorium']:
  r=c.post('/api/events',headers=h,json={**payload,'venue_mode':mode});assert r.status_code==201,r.text
 with sessions.begin() as db:
  e=Event(host_id=u['id'],title='Existing arena',city='london',starts_at=time.time(),venue_mode='grand_arena',venue_experience_type='auditorium');db.add(e);db.flush();id=e.id
 r=c.post('/api/events/'+id+'/venue/booking',headers=h,json={'request_id':str(uuid.uuid4()),'hours':1,'expected_cost':100})
 assert r.status_code==409 and 'Coming Soon' in r.text
 assert c.get('/api/venue-rentals/london',headers=h).json()['enabled'] is False
