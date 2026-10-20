from backend.tests.test_core import system, register, onboard
from backend.api.auth import display_profile
from backend.api.models import User

def test_profile_visibility_and_private_defaults(system):
    c, sessions = system
    a, ua = register(c, 'profile_alice'); b, ub = register(c, 'profile_bob')
    onboard(c,a); onboard(c,b)
    p = {'identity':'Non-binary','custom_identity':'','show_identity':False,'country':'United Kingdom','town':'Milton Keynes','area':'Whitehouse','show_location':False}
    assert c.put('/api/me/profile',json=p).status_code == 401
    assert c.put('/api/me/profile',headers=a,json=p).status_code == 200
    peer = next(x for x in c.get('/api/people',headers=b).json() if x['id']==ua['id'])
    assert 'identity' not in peer and 'display_location' not in peer
    p['show_location']=True
    assert c.put('/api/me/profile',headers=a,json=p).status_code == 200
    peer=next(x for x in c.get('/api/world/london',headers=b).json()['players'] if x['id']==ua['id'])
    assert peer['display_location']=={'country':'United Kingdom','town':'Milton Keynes','area':'Whitehouse'}
    assert 'identity' not in peer
    invite=c.post('/api/talk/request',headers=a,json={'target_id':ub['id'],'kind':'text'})
    assert invite.status_code==200
    assert c.get('/api/talk/state',headers=b).json()[0]['peer']['display_location']['area']=='Whitehouse'
    p['show_location']=False
    c.put('/api/me/profile',headers=a,json=p)
    assert 'display_location' not in c.get('/api/talk/state',headers=b).json()[0]['peer']
    assert c.get('/api/me',headers=a).json()['profile']['identity']=='Non-binary'
    assert c.get('/api/me',headers=b).json()['profile']['identity']=='Prefer not to say'
    assert not c.get('/api/me',headers=b).json()['profile']['show_location']
    assert c.put('/api/me/profile',headers=a,json={**p,'latitude':51}).status_code==422
    assert c.put('/api/me/profile',headers=a,json={**p,'country':'x'*81}).status_code==422

def test_identity_choices_and_avatar_independence(system):
    c,_=system
    for i,identity in enumerate(['Male','Female','Transgender','Non-binary','Prefer not to say','Custom / Other']):
        r=c.post('/api/auth/register',json={'username':f'identity_{i}','email':f'identity_{i}@example.test','password':'A secure test password 2026!','adult':True,'accepted_terms':True,'profile':{'identity':identity}})
        assert r.status_code==201
        h={'Authorization':'Bearer '+r.json()['token']}
        assert r.json()['user']['profile']['identity']==identity
        onboard(c,h)
        assert c.get('/api/me',headers=h).json()['avatar']=={'color':'#50ddab'}
        assert not r.json()['user']['profile']['show_identity']

def test_rankings_own_rank_preserves_existing_scores(system):
    c,_=system
    h,u=register(c,'rank_owner');onboard(c,h)
    d=c.get('/api/rankings?period=all&metric=xp',headers=h).json()
    assert d['own'] is None and d['rows']==[]
    config=c.get('/api/config').json()
    assert next(x for x in config['cities'] if x['id']=='milton-keynes')['name']=='Milton Keynes - Whitehouse'
