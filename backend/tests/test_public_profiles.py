from backend.tests.test_core import system, register, onboard


def test_profile_persistence_visibility_and_names(system):
    c, _ = system
    a, ua = register(c, 'profile_new_a'); b, ub = register(c, 'profile_new_b')
    onboard(c,a); onboard(c,b)
    payload = {'display_name':'Alice', 'bio':'Making music', 'theme':'Aurora',
               'links':{'instagram':{'url':'@alice'}, 'linkedin':{'url':'alice', 'visible':False}},
               'username':'renamed_alice', 'public_interests':['Music']}
    r = c.put('/api/me/profile',headers=a,json=payload)
    assert r.status_code == 200, r.text
    view = c.get('/api/profiles/by-name/RENAMED_ALICE',headers=b)
    assert view.status_code == 200, view.text
    p=view.json()
    assert p['id']==ua['id'] and p['bio']=='Making music'
    assert p['links']=={'instagram':'https://www.instagram.com/alice'}
    assert 'email' not in p and 'profile' not in p and 'display_location' not in p
    assert p['counts']=={'followers':0,'following':0,'friends':0,'events':0}
    assert c.get('/api/profiles/'+ua['id']).status_code==401
    assert c.put('/api/me/profile',headers=a,json={'username':ub['username'].upper()}).status_code==409
    assert c.put('/api/me/profile',headers=a,json={'country':'UK'}).status_code==200
    assert c.get('/api/me',headers=a).json()['profile']['bio']=='Making music'
    assert 'no-store' in c.get('/api/profiles/'+ua['id'],headers=b).headers['cache-control']
    assert c.post('/api/social/'+ua['id']+'/block',headers=b,json={}).status_code==200
    assert c.get('/api/profiles/'+ua['id'],headers=b).status_code==404
    assert c.get('/api/profiles/'+ub['id'],headers=a).status_code==404


def test_profile_url_validation_and_independent_social_edges(system):
    c,_=system
    a,ua=register(c,'profile_links_a');b,ub=register(c,'profile_links_b')
    onboard(c,a);onboard(c,b)
    for platform,url in [('instagram','javascript:alert(1)'),('instagram','https://instagram.com.evil.test/alice'),('website','https://user:password@example.com'),('website','https://127.0.0.1'),('instagram','https://www.instagram.com/redirect?url=evil'),('unrecognised','@foo')]:
        assert c.put('/api/me/profile',headers=a,json={'links':{platform:{'url':url}}}).status_code==422
    assert c.post('/api/social/'+ub['id']+'/follow',headers=a,json={}).status_code==200
    assert c.post('/api/social/'+ub['id']+'/friend',headers=a,json={}).status_code==200
    assert c.post('/api/social/'+ua['id']+'/accept',headers=b,json={}).status_code==200
    assert c.post('/api/social/'+ub['id']+'/unfollow',headers=a,json={}).status_code==200
    state=c.get('/api/profiles/'+ub['id'],headers=a).json()
    assert state['relationship']['friend'] and not state['relationship']['following']
    assert state['counts']['friends']==1 and state['counts']['followers']==0
    onboard(c,b,privacy='Ghost Mode')
    assert c.get('/api/profiles/'+ub['id'],headers=a).status_code==404
    assert c.post('/api/social/'+ub['id']+'/follow',headers=a,json={}).status_code==404


def test_profile_photos_authorization_export_and_removal(system):
    import base64, io
    from PIL import Image
    c,_=system
    a,ua=register(c,'photo_a');b,ub=register(c,'photo_b')
    onboard(c,a);onboard(c,b)
    image=io.BytesIO();Image.new('RGB',(500,500),'purple').save(image,format='PNG')
    content=base64.b64encode(image.getvalue()).decode()
    assert c.put('/api/me/photos/picture',json={'content':content}).status_code==401
    for kind in ('picture','cover'):
        r=c.put('/api/me/photos/'+kind,headers=a,json={'content':content})
        assert r.status_code==200,r.text
        photo=c.get(r.json()['url'],headers=b)
        assert photo.status_code==200 and photo.headers['content-type']=='image/jpeg'
        decoded=Image.open(io.BytesIO(photo.content))
        assert decoded.size==((384,384) if kind=='picture' else (1200,400))
        assert not decoded.getexif()
    assert c.put('/api/me/photos/picture',headers=a,json={'content':base64.b64encode(b'<svg/>').decode()}).status_code==422
    assert len(c.get('/api/privacy/export',headers=a).json()['profile_photos'])==2
    assert c.delete('/api/me/photos/cover',headers=b).status_code==200
    assert c.get('/api/profiles/'+ua['id']+'/photos/cover',headers=a).status_code==200
    assert c.post('/api/social/'+ua['id']+'/block',headers=b,json={}).status_code==200
    assert c.get('/api/profiles/'+ua['id']+'/photos/picture',headers=b).status_code==404
    assert c.delete('/api/me/photos/picture',headers=a).status_code==200
    assert c.get('/api/profiles/'+ua['id']+'/photos/picture',headers=a).status_code==404
    assert c.delete('/api/me',headers=a).status_code==200
    from backend.api.profile_media import ProfilePhoto
    with system[1]() as db:
        assert db.get(ProfilePhoto,(ua['id'],'cover')) is None
