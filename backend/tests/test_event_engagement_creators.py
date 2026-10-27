import time,uuid
from backend.tests.test_core import system,register,onboard
from backend.api.economy import credit

def test_live_polls_questions_and_authorised_highlights(system):
 c,dbs=system;host,owner=register(c,'stage_host');guest,user=register(c,'stage_guest')
 for h in [host,guest]:onboard(c,h)
 e=c.post('/api/events',headers=host,json={'title':'Creator audience test','city':'london','starts_at':time.time()+300,'event_type':'Public Talk'}).json();url='/api/events/'+e['id']
 assert c.post(url+'/join',headers=guest).status_code==200
 assert c.post(url+'/state/start',headers=host).status_code==200
 poll={'question':'What should we discuss?','options':['Cities','Music']}
 assert c.post(url+'/polls',headers=guest,json=poll).status_code==403
 result=c.post(url+'/polls',headers=host,json=poll);assert result.status_code==200,result.text
 pid=result.json()['polls'][0]['id']
 for _ in range(2):assert c.post(url+'/polls/'+pid+'/vote',headers=guest,json={'option':1}).status_code==200
 state=c.get(url,headers=guest).json()['engagement'];assert state['polls'][0]['counts']==[0,1]
 assert c.post(url+'/polls/'+pid+'/vote',headers=guest,json={'option':3}).status_code==422
 assert c.post(url+'/polls/'+pid+'/close',headers=host).status_code==200
 assert c.post(url+'/polls/'+pid+'/vote',headers=guest,json={'option':0}).status_code==409
 q=c.post(url+'/questions',headers=guest,json={'body':'How can we host?'}).json()['questions'][0]
 assert c.put(url+'/questions/'+q['id'],headers=guest,json={'answer':'Spoofed'}).status_code==403
 assert c.put(url+'/questions/'+q['id'],headers=host,json={'answer':'Use the booking calendar','hidden':True}).status_code==200
 assert c.get(url,headers=guest).json()['engagement']['questions']==[]
 image={'title':'Authorised artwork','image_url':'https://example.test/owned-poster.png','rights_confirmed':True,'participants_consented':False}
 assert c.post(url+'/highlights',headers=host,json=image).status_code==422
 image['participants_consented']=True
 assert c.post(url+'/highlights',headers=guest,json=image).status_code==403
 r=c.post(url+'/highlights',headers=host,json=image);assert r.status_code==201,r.text
 profile=c.get('/api/creators/'+owner['id'],headers=guest);assert profile.status_code==200,profile.text
 assert profile.json()['events'][0]['highlights'][0]['title']==image['title']
 from backend.api.events import view
 from backend.api.models import Event,User
 with dbs() as db:
  snapshot=view(db,db.get(Event,e['id']),db.get(User,owner['id']),compact=True)
  assert snapshot['engagement'] is None and snapshot['ticketing'] is None
  assert 'highlights' not in snapshot['programme'] and 'questions' not in snapshot['programme']
 assert c.delete(url+'/highlights/'+r.json()['id'],headers=host).status_code==200
 assert c.get(url,headers=guest).json()['programme']['highlights']==[]

def test_private_paid_event_requires_approval_then_ticket(system):
 c,dbs=system;host,owner=register(c,'private_host');guest,user=register(c,'private_guest')
 for h in [host,guest]:onboard(c,h)
 e=c.post('/api/events',headers=host,json={'title':'Private paid discussion','city':'london','starts_at':time.time()+300,'visibility':'private','ticket_price':10}).json();url='/api/events/'+e['id']
 assert c.get(url,headers=guest).status_code==404
 assert c.post(url+'/invite',headers=host,json={'user_id':user['id']}).status_code==200
 with dbs.begin() as db:credit(db,user['id'],100,'purchase','test','private-ticket-fixture')
 purchase={'request_id':str(uuid.uuid4()),'expected_cost':10}
 assert c.post(url+'/tickets',headers=guest,json=purchase).status_code==403
 assert c.post(url+'/join',headers=guest).json()['my_state']=='pending'
 assert c.post(url+'/people/'+user['id']+'/approve',headers=host).status_code==200
 detail=c.get(url,headers=guest).json();assert detail['my_state']=='approved' and not detail['joined']
 assert c.post(url+'/join',headers=guest).status_code==402
 assert c.post(url+'/tickets',headers=guest,json=purchase).status_code==200
 assert c.post(url+'/join',headers=guest).json()['joined'] is True
 assert c.get('/api/creators/'+owner['id'],headers=guest).json()['events']==[]
