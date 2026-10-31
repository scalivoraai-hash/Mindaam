"""Local ledger invariants; these do not attest a real Stripe sandbox purchase."""
import time, uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from sqlalchemy import select, func
from backend.tests.test_core import system, register, onboard
from backend.api.models import Ledger, Collectible, Presence, MissionCompletion, Mission
from backend.api.economy import credit, balance


def test_one_hundred_gems_and_missions_never_mint_pc(system):
 c,sessions=system;h,u=register(c);onboard(c,h)
 with sessions.begin() as db:
  # Explicit local world fixtures, claimed through the real authoritative API.
  db.add(Mission(id="local-gem-mission",city="london",title="Local 100 gem mission",description="XP only",requirements={"gem":100},credits=50,xp=50))
  for i in range(100):db.add(Collectible(id='xp-only-'+str(i),city='london',kind='gem',x=0,z=0,title='Local XP test'))
  p=db.get(Presence,u['id']);p.x=p.z=0
 for i in range(100):
  r=c.post('/api/collectibles/xp-only-'+str(i)+'/claim',headers=h)
  assert r.status_code==200,r.text
  assert r.json()['awarded_credits']==0
 with sessions() as db:
  assert balance(db,u['id'])==0
  assert balance(db,u['id'],'xp')>=1570
  assert db.scalar(select(func.count()).select_from(MissionCompletion).where(MissionCompletion.mission_id=='local-gem-mission'))==1
  assert not db.scalar(select(func.count()).select_from(Ledger).where(Ledger.currency=='credits',Ledger.amount>0))

@pytest.mark.parametrize('kind',['welcome','mission','collectible','daily','referral','visit','admin_promotion','admin_support','admin_correction','unknown'])
def test_nonpurchase_pc_mint_denied(system,kind):
 c,sessions=system;h,u=register(c);onboard(c,h)
 with sessions.begin() as db:
  with pytest.raises(HTTPException) as error:credit(db,u['id'],20,kind,'local','local-'+kind)
  assert error.value.status_code==409
  assert balance(db,u['id'])==0


def prepare_ticket(system):
 c,sessions=system;h,host=register(c,'host');onboard(c,h);g,guest=register(c,'guest');onboard(c,g)
 with sessions.begin() as db:credit(db,guest['id'],100,'purchase','local-fixture','local-funded-attendee')
 r=c.post('/api/events',headers=h,json={'title':'Local conserved transfer','city':'london','starts_at':time.time(),'venue_mode':'standard','ticket_price':20})
 assert r.status_code==201,r.text
 return c,sessions,h,host,g,guest,'/api/events/'+r.json()['id']


def test_atomic_ticket_transfer_and_duplicate_refund(system):
 c,sessions,h,host,g,guest,url=prepare_ticket(system)
 data={'request_id':str(uuid.uuid4()),'expected_cost':20}
 with ThreadPoolExecutor(max_workers=3) as pool:replies=list(pool.map(lambda _:c.post(url+'/tickets',headers=g,json=data),range(3)))
 assert all(r.status_code==200 for r in replies),[r.text for r in replies]
 assert len({r.json()['id'] for r in replies})==1
 ticket_id=replies[0].json()['id']
 with sessions() as db:
  assert (balance(db,guest['id']),balance(db,host['id']))==(80,20)
  entries=list(db.scalars(select(Ledger).where(Ledger.source==ticket_id)))
  assert len(entries)==2 and sum(r.amount for r in entries)==0
 assert c.post(url+'/tickets',headers=h,json=data).status_code==409
 for _ in range(2):
  r=c.post(url+'/state/cancel',headers=h);assert r.status_code==200,r.text
 with sessions() as db:
  assert (balance(db,guest['id']),balance(db,host['id']))==(100,0)
  assert sum(db.scalars(select(Ledger.amount).where(Ledger.source==ticket_id)))==0


def test_missing_organiser_refund_funds_rolls_back(system):
 c,sessions,h,host,g,guest,url=prepare_ticket(system)
 assert c.post(url+'/tickets',headers=g,json={'request_id':str(uuid.uuid4()),'expected_cost':20}).status_code==200
 with sessions.begin() as db:credit(db,host['id'],-20,'event_gift','local-spend','local-spend')
 assert c.post(url+'/state/cancel',headers=h).status_code==409
 with sessions() as db:
  assert balance(db,guest['id'])==80
  assert balance(db,host['id'])==0
  assert not db.scalar(select(func.count()).select_from(Ledger).where(Ledger.kind=='event_ticket_refund'))
