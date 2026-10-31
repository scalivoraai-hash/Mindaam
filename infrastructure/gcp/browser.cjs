/* GCP staging only: actual HTTPS/WebRTC, synthetic capture, no database fixtures. */
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const {chromium}=require(process.env.QA_NODE_MODULES+'/playwright');
const release=JSON.parse(fs.readFileSync('deployment-result.json'));
assert.equal(release.environment,'staging');
const {required,safeText,safeUrl,validatePolicy}=require('./browser-contract.cjs');
const betaPolicy=require('./beta-policy.json'),beta=release.profile===betaPolicy.profile;
const acceptanceRequired=beta?[...required.filter(k=>k!=='venue_booking'),...betaPolicy.additional_checks.filter(k=>k!=='direct_webrtc'||process.env.QA_FORCE_TURN!=='1')]:required;
const origin=release.origin;assert.match(origin,/^https:\/\/[a-z0-9.-]+\.run\.app$/);
const out='gcp-evidence';fs.mkdirSync(out,{recursive:true});
const {act,inspectControl,expectedAnonymous}=require('./browser-ui.cjs');
const {authenticateAndEnter}=require('./browser-flow.cjs');
const activeUsers=[],sensitive=[],mode=process.env.QA_FORCE_TURN==='1'?'relay':'direct';let stage='initialization';
const mixedRenderer=false,errors=[],wait=ms=>new Promise(r=>setTimeout(r,ms));let browser;
async function until(fn,label,timeout=25000){const end=Date.now()+timeout;let error;while(Date.now()<end){try{const value=await fn();if(value)return value}catch(e){error=e}await wait(200)}throw Error(label+' timed out'+(error?' · '+error.message:''))}
async function ready(url){return until(async()=>{try{return(await fetch(url,{signal:AbortSignal.timeout(3000)})).ok}catch{return false}},'Ready '+url,90000)}
async function user(city,index){
 const touch=index===2;const context=await browser.newContext({viewport:touch?{width:390,height:844}:{width:1100,height:760},isMobile:touch,hasTouch:touch,permissions:['camera','microphone']});
 if(mixedRenderer)await context.addInitScript(({observer})=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){if((kind==='webgl'||kind==='webgl2')&&(!observer||!document.querySelector('.world-playing')))return null;return get.call(this,kind,...args)}},{observer:index===1});
 await context.addInitScript(()=>{
  const Native=window.WebSocket;window.WebSocket=new Proxy(Native,{construct(Target,args){const socket=Reflect.construct(Target,args);socket.addEventListener('message',event=>{try{const d=JSON.parse(event.data);if(['state','motion'].includes(d.type)&&d.position&&(d.position.last_move||0)>=(window.__qaMotion?.last_move||0)){window.__qaMotion=d.position;window.dispatchEvent(new CustomEvent('qa-motion',{detail:d.position}))}}catch{}});return socket}});
 });
 await context.addInitScript(()=>{window.__qaFrames=[];window.__qaMedia=[];window.addEventListener('pulse-avatar-anchors',e=>{window.__qaAnchors=e.detail;window.__qaAnchorViewport={width:innerWidth,height:innerHeight}});window.addEventListener('pulse-media-status',e=>window.__qaMedia.push(e.detail));});
 await context.addInitScript(({relay})=>{
  window.__gcpPeers=[];
  const Native=window.RTCPeerConnection;
  const restrict=c=>relay?{...c,iceTransportPolicy:'relay',iceServers:(c.iceServers||[]).map(s=>({...s,urls:[s.urls].flat().filter(u=>u.startsWith('turns:')&&u.includes(':443'))})).filter(s=>s.urls.length)}:c;
  window.RTCPeerConnection=new Proxy(Native,{construct(Target,args){
   const pc=Reflect.construct(Target,[restrict(args[0]||{}),...args.slice(1)]);
   const set=pc.setConfiguration.bind(pc);pc.setConfiguration=c=>set(restrict(c));
   window.__gcpPeers.push(pc);return pc;
  }});
 },{relay:process.env.QA_FORCE_TURN==='1'});
 // Observe the existing timeout without changing requests, signals or deadlines.
 await context.addInitScript(()=>{
  window.__qaRequests=[];window.__qaLoopDelays=[];
  const record=v=>{window.__qaRequests.push(v);if(window.__qaRequests.length>100)window.__qaRequests.shift()};
  const route=value=>{try{return new URL(typeof value==='string'?value:value.url,location.href).pathname.replace(/[a-f0-9]{8}-[a-f0-9-]{27,}/gi,'[id]')}catch{return '[unknown]'}};
  const original=window.fetch.bind(window);
  window.fetch=async(...args)=>{
   const start=performance.now(),path=route(args[0]),method=args[1]?.method||'GET';
   try{
    const response=await original(...args),headersAt=performance.now();
    const json=response.json.bind(response);
    response.json=async()=>{try{return await json()}catch(error){record({path,method,phase:'body',name:error.name,status:response.status,elapsed:performance.now()-start,headers_ms:headersAt-start});throw error}};
    if(headersAt-start>1000)record({path,method,phase:'headers',status:response.status,elapsed:headersAt-start});
    return response;
   }catch(error){record({path,method,phase:'fetch',name:error.name,elapsed:performance.now()-start});throw error}
  };
  let tick=performance.now();setInterval(()=>{const now=performance.now(),delay=now-tick-250;tick=now;if(delay>1000){window.__qaLoopDelays.push({at:Date.now(),delay});if(window.__qaLoopDelays.length>30)window.__qaLoopDelays.shift()}},250);
 });
 const page=await context.newPage(),states=[],logs=[],inputs=[],failures=[],grants=[];
 const u={context,page,states,logs,inputs,failures,grants,touch,index,authExpected:false};activeUsers.push(u);
 page.setDefaultTimeout(60000);page.setDefaultNavigationTimeout(90000);
 page.on('response',async response=>{const url=safeUrl(response.url());if(response.status()>=400)failures.push({url,status:response.status(),expected:expectedAnonymous(response,u)});if(/\/api\/media\/[^/]+\/token$/.test(new URL(url).pathname)&&response.ok()){try{const g=await response.json();sensitive.push(g.token);grants.push({host:new URL(g.url).hostname,policy:g.media_policy,can_speak:g.can_speak})}catch{}}if(failures.length>80)failures.shift()});
 page.on('requestfailed',request=>{failures.push({url:safeUrl(request.url()),error:safeText(request.failure()?.errorText,sensitive)});if(failures.length>80)failures.shift()});
 page.on('pageerror',e=>errors.push({index,error:safeText(e.message,sensitive)}));
 page.on('console',m=>{if(['warning','error'].includes(m.type())){logs.push(safeText(m.text(),sensitive));if(logs.length>80)logs.shift()}});
 page.on('websocket',ws=>{if(ws.url().endsWith('/api/realtime')){ws.on('framesent',frame=>{try{const d=JSON.parse(frame.payload.toString());if(d.type==='input'){inputs.push({at:Date.now(),...d});if(inputs.length>120)inputs.shift()}}catch{}});ws.on('framereceived',frame=>{try{const d=JSON.parse(frame.payload.toString());if(d.type==='state'){states.push(d);if(states.length>80)states.shift()}}catch{}})}});
 const api=async(route,data,method=data===undefined?'GET':'POST')=>{const res=await context.request.fetch(origin+'/api'+route,{method,data,headers:{Origin:origin,'X-Pulse-Client':'web'}});if(!res.ok())throw Error('API '+safeUrl(origin+'/api'+route)+' HTTP '+res.status());return res.json()};
 let name='gcpqa'+Date.now().toString(36)+index;const reusable=!beta&&index===0&&!!process.env.QA_STAGING_HOST_IDENTIFIER;const password=reusable?process.env.QA_STAGING_HOST_PASSWORD:crypto.randomBytes(24).toString('base64url')+'!aA1';assert.ok(password,'Reusable staging host password is required');u.reusable=reusable;
 sensitive.push(password);if(reusable)sensitive.push(process.env.QA_STAGING_HOST_IDENTIFIER);u.api=api;stage='signup-'+index;
 await authenticateAndEnter(u,{origin,city,index,password,identifier:process.env.QA_STAGING_HOST_IDENTIFIER,name,reusable,until,setStage:value=>stage=value});
 return u;
}
async function settled(users){
 await Promise.all(users.map(u=>move(u,0,0)));let stableSince=Date.now(),previous=JSON.stringify(users.map(position));
 await until(()=>{const next=JSON.stringify(users.map(position));if(next!==previous){previous=next;stableSince=Date.now()}return Date.now()-stableSince>1800&&users.every(u=>(u.states.at(-1)?.server_time||0)*1000>Date.now()-1500)},'Stopped positions',12000);
 return users.map(position);
}
const position=u=>{const p=u.states.at(-1)?.position;return p&&{x:p.x,z:p.z,zone:p.zone_id}};
const peer=(u,id)=>u.states.at(-1)?.players.find(p=>p.id===id);
async function controls(u,which){
 const name=which.source==='Reconnect|Join LiveFace'?/^(?:Reconnect|🎥 Join LiveFace)$/:new RegExp('^(?:'+which.source+')$');
 await act(u,u.page.locator('.live-dock').getByRole('button',{name}),'LiveFace '+which.source);
}
async function video(u,id){return until(()=>u.page.locator('.remote-tile[data-peer-id="'+id+'"] video:not([hidden])').evaluateAll(v=>v.some(el=>el.videoWidth>0&&el.readyState>=2)),'Decoded remote video')}
async function audio(u,id){const enable=u.page.getByRole('button',{name:/Audio is ready. Tap to listen/});if(await enable.count())await act(u,enable,'Enable remote audio');return until(()=>u.page.locator('.remote-tile[data-peer-id="'+id+'"] audio').evaluateAll(async elements=>{
  const el=elements.find(e=>e.srcObject&&!e.muted);if(!el)return false;
  const ac=new AudioContext();await ac.resume();const source=ac.createMediaStreamSource(el.srcObject),analyser=ac.createAnalyser();source.connect(analyser);await new Promise(r=>setTimeout(r,180));const values=new Float32Array(analyser.fftSize);analyser.getFloatTimeDomainData(values);const rms=Math.sqrt(values.reduce((s,x)=>s+x*x,0)/values.length);source.disconnect();await ac.close();return rms>.002;
 }),'Non-silent remote audio')}
async function move(u,x,z){await u.page.evaluate(({x,z})=>window.dispatchEvent(new CustomEvent('pulse-drive-input',{detail:[x,z]})),{x,z})}
async function screenshot(u,name){await u.page.screenshot({path:path.join(out,name+'.jpg'),type:'jpeg',quality:75,timeout:60000})}

async function sentTracks(u){return u.page.evaluate(()=>window.__gcpPeers.flatMap(p=>p.getSenders()).filter(s=>s.track?.readyState==='live').length)}
async function relay(u){return until(()=>u.page.evaluate(async()=>{
 for(const pc of window.__gcpPeers){const stats=await pc.getStats();for(const s of stats.values()){
  if(s.type==='candidate-pair'&&s.state==='succeeded'&&s.nominated){const local=stats.get(s.localCandidateId);if(local?.candidateType==='relay'&&local.url?.startsWith('turns:')&&local.url.includes(':443'))return true;
 }} }return false;
}),'Selected TURN/TLS 443 candidate',45000)}
async function diagnostics(error){
 for(const u of activeUsers){const prefix=path.join(out,mode+'-failure-'+u.index);
  const data={stage,error:safeText(error.message,sensitive),url:safeUrl(u.page.url()),control:u.failedControl|| (u.lastControl?{label:u.lastControl.label,...await inspectControl(u.lastControl.locator).catch(()=>({inspection_failed:true}))}:null),console:u.logs,network:u.failures,errors};
  try{await u.page.bringToFront();data.auth_controls=await inspectControl(u.page.locator('.auth-card button, .auth-card a'));data.requests=await u.page.evaluate(()=>({requests:window.__qaRequests,loop_delays:window.__qaLoopDelays}));data.title=safeText(await u.page.title(),sensitive);data.body=safeText(await u.page.locator('body').innerText({timeout:4000}),sensitive);
   data.state=await u.page.evaluate(()=>({world:!!document.querySelector('.world-playing'),ready:document.querySelector('.world-canvas')?.getAttribute('data-ready'),welcome:!!document.querySelector('.welcome-home'),onboarding:!!document.querySelector('.onboarding'),media:window.__gcpPeers.map(p=>({connection:p.connectionState,ice:p.iceConnectionState,senders:p.getSenders().filter(s=>s.track?.readyState==='live').length}))}));
   const response=await u.context.request.get(origin+'/api/me');const me=response.ok()?await response.json():null;data.auth={status:response.status(),expected_anonymous:response.status()===401&&u.authExpected===false};if(me)data.user={id:me.id,onboarded:me.onboarded,city:me.city};
  }catch{data.collection_incomplete=true}
  await u.page.screenshot({path:prefix+'.jpg',type:'jpeg',quality:65,timeout:5000,mask:[u.page.locator('input,textarea,pre,code')]}).catch(()=>{data.screenshot_failed=true});
  fs.writeFileSync(prefix+'.json',JSON.stringify(data,null,2));
 }
 fs.writeFileSync(path.join(out,mode+'-failure.json'),JSON.stringify({stage,error:safeText(error.message,sensitive)},null,2));
}

async function main(){
 // 20 seconds of a sine wave, consumed by Chromium's fake microphone.
 const samples=48000*20,wav=Buffer.alloc(44+samples*2);wav.write('RIFF');wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(48000,24);wav.writeUInt32LE(96000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(samples*2,40);for(let i=0;i<samples;i++)wav.writeInt16LE(Math.round(8000*Math.sin(2*Math.PI*440*i/48000)),44+i*2);fs.writeFileSync('/tmp/mindaam-tone.wav',wav);
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--auto-select-desktop-capture-source=Entire screen','--use-file-for-fake-audio-capture=/tmp/mindaam-tone.wav','--disable-background-timer-throttling']});
 const readinessContext=await browser.newContext();
 let readinessLast='not ready';
 const health=await until(async()=>{
  try{
   const response=await readinessContext.request.get(origin+'/api/health',{timeout:5000});
   const contentType=(response.headers()['content-type']||'').toLowerCase();
   if(!response.ok()){readinessLast='HTTP '+response.status();return false}
   if(!contentType.includes('application/json')){readinessLast='content-type '+contentType;return false}
   const value=await response.json();
   if(value?.environment!=='staging'||value?.status!=='ready'){readinessLast='unexpected health body';return false}
   return value;
  }catch(error){readinessLast=error.message;return false}
 },'Staging health JSON via Playwright',120000).catch(error=>{throw Error(error.message+' · last='+readinessLast)});
 await readinessContext.close();
 assert.equal(health.environment,'staging');assert.equal(health.status,'ready');
 const users=[],checks={},result={sha:release.sha,origin,profile:release.profile||'full',deferred:beta?betaPolicy.deferred:{},checks,synthetic_capture:true,forced_turn:process.env.QA_FORCE_TURN==='1'};let event;
 try{
  const a=await user('milton-keynes',0);users.push(a);const b=await user('milton-keynes',1);users.push(b);
  stage='ordinary-world';
  assert.equal(await a.page.evaluate(()=>window.__gcpPeers.length),0,'Ordinary world must not create media connections');
  await a.api('/social/'+b.id+'/friend',{});await b.api('/social/'+a.id+'/accept',{});
  for(const u of [a,b]){assert.equal(await u.page.evaluate(()=>window.__gcpPeers.length),0);assert.ok((await u.api('/friends')).some(p=>p.friend&&p.id===(u===a?b.id:a.id)))}
  await act(a,a.page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'PEOPLE',exact:true}),'Acceptance control');
  await a.page.getByRole('heading',{name:'Your people',exact:true}).waitFor();await act(a,a.page.getByRole('tab',{name:'Friends',exact:true}),'Acceptance control');
  stage='settings-feedback';
  await act(a,a.page.getByRole('button',{name:'Close panel',exact:true}),'Close people panel');
  await act(a,a.page.getByRole('button',{name:'Account settings',exact:true}),'Open Settings');
  await act(a,a.page.getByRole('button',{name:'Edit Profile · Identity, Location & Avatar',exact:true}),'Edit Profile');
  assert.equal(await a.page.getByRole('heading',{name:'Help Shape Mindaam',exact:true}).count(),0);
  const profileForm=a.page.locator('.profile-editor');await profileForm.getByLabel('Display name',{exact:true}).fill('Staging settings acceptance');
  await act(a,profileForm.getByRole('button',{name:'Save Profile',exact:true}),'Save existing profile');
  await profileForm.getByText('Profile saved.',{exact:true}).waitFor();assert.equal((await a.api('/me')).profile.display_name,'Staging settings acceptance');
  await act(a,a.page.getByRole('button',{name:'Close panel',exact:true}),'Close profile');
  await act(a,a.page.getByRole('button',{name:'Account settings',exact:true}),'Open Settings');
  await act(a,a.page.getByRole('button',{name:'Help Shape Mindaam',exact:true}),'Open feedback');
  const feedbackForm=a.page.getByRole('dialog',{name:'Help Shape Mindaam',exact:true}).locator('form');assert.equal(await feedbackForm.count(),1);
  for(const category of ['feature','feedback']){
   await feedbackForm.getByRole('combobox',{name:/^Category/}).selectOption(category);
   await feedbackForm.getByLabel('Title',{exact:true}).fill('Staging acceptance '+category);
   await feedbackForm.getByLabel('Description',{exact:true}).fill('Disposable staging acceptance of the existing Settings feedback form.');
   const response=a.page.waitForResponse(r=>new URL(r.url()).pathname==='/api/feedback'&&r.request().method()==='POST');
   await act(a,feedbackForm.getByRole('button',{name:'Submit',exact:true}),'Submit '+category);assert.equal((await response).status(),201);
   await feedbackForm.getByText('Thank you. Your submission has been saved for review.',{exact:true}).waitFor();
  }
  for(const size of [{width:390,height:844},{width:820,height:1180},{width:1180,height:820},{width:1440,height:900}]){
   await a.page.setViewportSize(size);assert.ok(await feedbackForm.locator('input,textarea,select,button').evaluateAll(es=>es.every(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1})));
   await screenshot(a,'settings-feedback-'+size.width+(result.forced_turn?'-turn':''));
  }
  await a.page.setViewportSize({width:1100,height:760});await act(a,a.page.getByRole('button',{name:'Close panel',exact:true}),'Close feedback');
  checks.settings_feedback=true;checks.profile_edit_preserved=true;
  await act(a,a.page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'PEOPLE',exact:true}),'Restore people panel');
  await a.page.getByRole('heading',{name:'Your people',exact:true}).waitFor();await act(a,a.page.getByRole('tab',{name:'Friends',exact:true}),'Restore friends tab');
  stage='profiles';await b.api('/me/profile',{display_name:'Staging profile check',bio:'Automated staging acceptance',links:{instagram:{url:'@mindaamqa',visible:true},facebook:{url:'mindaamqa',visible:false}}},'PUT');
  await act(a,a.page.locator('.friend-card').filter({hasText:b.username}).getByRole('button',{name:'View profile',exact:true}),'Acceptance control');const profile=a.page.getByRole('dialog',{name:'Player profile',exact:true});await profile.getByRole('heading',{name:'Staging profile check',exact:true}).waitFor();assert.equal(await profile.locator('a[href*="facebook.com"]').count(),0);await act(a,profile.getByRole('button',{name:'Follow',exact:true}),'Player profile control');await profile.getByRole('button',{name:'Unfollow',exact:true}).waitFor();await act(a,profile.getByRole('button',{name:'Avatar',exact:true}),'Player profile control');await profile.locator('.avatar-preview canvas').waitFor();assert.equal(await profile.getByText('3D preview is unavailable in this browser.',{exact:false}).count(),0);await act(a,profile.getByRole('button',{name:'Close profile',exact:true}),'Player profile control');checks.profiles=true;checks.avatar_rendering=true;
  await act(a,a.page.getByRole('button',{name:'Close panel',exact:true}),'Acceptance control');
  for(const key of ['browser','signup','login','onboarding','session_persistence','world_entry','friends','no_world_media'])checks[key]=true;
  stage='free-events';
  const standard=await a.api('/events',{title:'GCP free standard acceptance '+Date.now(),city:'milton-keynes',starts_at:Date.now()/1000,communication_mode:'text',venue_mode:'standard',ticket_price:0});
  await a.api('/events/'+standard.id+'/state/start',{});await b.api('/events/'+standard.id+'/join',{});
  assert.equal((await b.api('/events/'+standard.id)).joined,true);await a.api('/events/'+standard.id+'/state/cancel',{});checks.free_events=true;
  const wallet=await a.api('/wallet');assert.ok(Number.isInteger(wallet.credits)&&wallet.credits>=0&&Number.isInteger(wallet.xp)&&wallet.xp>=0&&Array.isArray(wallet.transactions));checks.wallet_read=true;
  for(const u of [a,b]){const denied=await u.context.request.get(origin+'/api/super-admin/overview');assert.equal(denied.status(),403)}
  const anonymous=await browser.newContext();assert.equal((await anonymous.request.get(origin+'/api/super-admin/overview')).status(),401);await anonymous.close();checks.admin_access_control=true;
  stage='events-auditorium';
  event=await a.api('/events',{title:'GCP free auditorium acceptance '+Date.now(),description:'Automated staging QA, synthetic devices.',city:'milton-keynes',starts_at:Date.now()/1000,communication_mode:'liveface',venue_mode:'virtual_auditorium',ticket_price:0,event_type:'Public Talk'});
  assert.equal(event.arena_booking_required,false);assert.equal(event.ticket_price,0);checks.free_auditorium=true;
  if(beta){
   const config=await a.api('/config');assert.equal(config.flags.payment_actions_enabled,false);assert.equal(config.flags.payments_enabled,false);
   const packs=await a.api('/payments/credits');assert.equal(packs.ready,false);assert.ok(packs.packs.length>0);
   const blocked=await a.context.request.post(origin+'/api/payments/checkout',{headers:{Origin:origin,'X-Pulse-Client':'web'},data:{sku:packs.packs[0].id,expected_amount:packs.packs[0].amount_pence,request_id:crypto.randomUUID()}});assert.equal(blocked.status(),409);
   const booking=await a.context.request.post(origin+'/api/events/'+event.id+'/venue/booking',{headers:{Origin:origin,'X-Pulse-Client':'web'},data:{request_id:crypto.randomUUID(),hours:1,starts_at:Date.now()/1000,expected_cost:100}});assert.equal(booking.status(),409);
   assert.deepEqual(await a.api('/wallet'),wallet);checks.payment_gate=true;
  }
  await a.api('/events/'+event.id+'/state/start',{});await b.api('/events/'+event.id+'/join',{});await b.api('/events/'+event.id+'/venue/enter',{});
  await until(()=>peer(a,b.id)&&peer(b,a.id),'Mutual realtime presence',60000);
  await until(()=>[a,b].every(u=>u.states.at(-1)?.scene?.id===event.id),'Both users entered auditorium',60000);checks.events=true;stage='movement';
  const start=position(a);await move(a,.4,0);await until(()=>Math.hypot(position(a).x-start.x,position(a).z-start.z)>.05,'Movement');await move(a,0,0);
  await until(()=>Math.abs(peer(b,a.id).x-position(a).x)<.5,'Remote movement');checks.multiplayer=true;checks.movement=true;stage='liveface';
  await controls(a,/Reconnect|Join LiveFace/);await until(()=>a.page.locator('.live-dock.is-connected').count(),'Host connection');
  assert.equal(await a.page.getByRole('button',{name:'Camera On',exact:true}).count(),1);assert.equal(await a.page.getByRole('button',{name:'Unmute',exact:true}).count(),1);
  assert.equal(await sentTracks(b),0,'Audience publishes no camera or microphone');
  await controls(a,/Camera On/);await controls(a,/Unmute/);await controls(b,/Expand/);
  await video(b,a.id);checks.video=true;await audio(b,a.id);checks.voice=true;
  const c=await user('milton-keynes',2);users.push(c);await c.api('/events/'+event.id+'/join',{});await c.api('/events/'+event.id+'/venue/enter',{});await controls(c,/Expand/);await video(c,a.id);await audio(c,a.id);assert.equal(await sentTracks(c),0);
  await a.api('/events/'+event.id+'/people/'+b.id+'/speaker',{});await until(()=>b.page.getByRole('button',{name:'Camera On',exact:true}).count(),'Stage promotion');await controls(b,/Camera On/);await controls(b,/Unmute/);await controls(a,/Expand/);await video(a,b.id);await audio(a,b.id);
  await a.api('/events/'+event.id+'/people/'+b.id+'/audience',{});await until(async()=>await sentTracks(b)===0,'Revoked audience publishing');checks.event_media=true;checks.audience_restrictions=true;
  await until(async()=>await b.page.getByRole('button',{name:'Camera On',exact:true}).count()===0&&await b.page.getByRole('button',{name:'Unmute',exact:true}).count()===0,'Audience camera and microphone controls removed');stage='screen-sharing';
  await act(a,a.page.locator('.event-share-controls').getByRole('button',{name:'Share screen',exact:true}),'Acceptance control');
  await until(()=>c.page.locator('.presentation-sources video[data-track-source="screen_share"]').evaluateAll(es=>es.some(e=>e.videoWidth>0&&e.readyState>=2)),'Actual decoded screen');checks.screen_share=true;
  await audio(c,a.id);await act(a,a.page.getByRole('button',{name:'Stop sharing',exact:true}),'Acceptance control');
  stage='auditorium-reentry';
  await b.api('/events/'+event.id+'/venue/exit',{});
  await until(()=>b.states.at(-1)?.position?.zone_id==='world','Audience returned to city',60000);
  await b.api('/events/'+event.id+'/venue/enter',{});
  await until(()=>b.states.at(-1)?.scene?.id===event.id,'Audience re-entered auditorium',60000);
  if(await b.page.locator('.live-dock').getByRole('button',{name:'Expand',exact:true}).count())await controls(b,/Expand/);
  await video(b,a.id);await audio(b,a.id);checks.auditorium_reentry=true;
  stage='responsive-policy';
  for(const size of [{width:390,height:844},{width:820,height:1180},{width:1440,height:900}]){await c.page.setViewportSize(size);await video(c,a.id);assert.ok(await c.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));await screenshot(c,'viewport-'+size.width+(result.forced_turn?'-turn':''));}
  checks.responsive=true;
  for(const u of users){assert.ok(u.grants.length,'Actual media grant required');for(const g of u.grants){assert.equal(g.host,'media.mindaam.com');validatePolicy(g.policy)}}checks.self_hosted_media=true;
  await controls(c,/Minimise/);await until(()=>c.page.locator('.remote-tile video[data-track-source="camera"]:not([hidden])').evaluateAll(es=>es.length>0&&es.every(e=>e.videoHeight>0&&e.videoHeight<=360)),'Decoded avatar video at most 360p',45000);
  await controls(c,/Full Screen/);await video(c,a.id);
  assert.ok(await c.page.locator('.remote-tile video:not([hidden])').evaluateAll(es=>es.length>0&&es.every(e=>e.videoHeight>0&&e.videoHeight<=720)),'Decoded full-screen cap');checks.startup_policy=true;
  const forbidden=await c.page.locator('.remote-tile[data-peer-id="'+b.id+'"] video:not([hidden])').count();assert.equal(forbidden,0,'Demoted audience video must not remain subscribed');
  assert.ok(await c.page.locator('.remote-tile video:not([hidden])').count()<=4);checks.selective_subscription=true;
  if(result.forced_turn){await relay(a);await relay(c);checks.turn_tls=true;}
  else if(beta){
   await until(()=>a.page.evaluate(async()=>{for(const pc of window.__gcpPeers){const stats=await pc.getStats();for(const pair of stats.values()){if(pair.type==='candidate-pair'&&pair.state==='succeeded'&&pair.nominated){const local=stats.get(pair.localCandidateId),remote=stats.get(pair.remoteCandidateId);if(local&&remote&&['host','srflx','prflx'].includes(local.candidateType)&&['host','srflx','prflx'].includes(remote.candidateType))return true}}}return false}),'Direct non-relay WebRTC candidate',45000);checks.direct_webrtc=true;
  }
  if(!beta){
   stage='paid-venue';
   await a.api('/events/'+event.id+'/state/cancel',{});
   event=await a.api('/events',{title:'GCP paid arena acceptance '+Date.now(),city:'milton-keynes',starts_at:Date.now()/1000,communication_mode:'liveface',venue_mode:'grand_arena',event_type:'Public Talk'});
  const catalogue=await a.api('/venue-rentals/milton-keynes'),cost=catalogue.prices?.['1'];
  const maxCost=Number(process.env.QA_STAGING_MAX_RESERVATION_PC||0);
  assert.ok(a.reusable&&catalogue.enabled&&Number.isInteger(cost)&&cost>0&&cost<=maxCost&&catalogue.purchased_credits>=cost,'Paid venue acceptance requires a dedicated purchased-credit staging host and an explicit per-reservation PC limit. No test credits are fabricated.');
  const reservation=await a.api('/events/'+event.id+'/venue/booking',{request_id:crypto.randomUUID(),hours:1,starts_at:Date.now()/1000,expected_cost:cost});assert.equal(reservation.cost,cost);checks.venue_booking=true;
   await a.api('/events/'+event.id+'/state/start',{});await b.api('/events/'+event.id+'/join',{});await b.api('/events/'+event.id+'/venue/enter',{});
   await until(()=>[a,b].every(u=>u.states.at(-1)?.scene?.id===event.id),'Paid auditorium entry',60000);
  }
  for(const key of acceptanceRequired)assert.equal(checks[key],true,'Missing acceptance '+key);
  assert.equal(errors.length,0,'No uncaught browser errors');
  result.request_observations=await Promise.all(activeUsers.map(async u=>({index:u.index,failures:u.failures,console:u.logs,...await u.page.evaluate(()=>({requests:window.__qaRequests,loop_delays:window.__qaLoopDelays,visible_error:document.querySelector('.toast.error')?.textContent||null}))})));
  fs.writeFileSync(path.join(out,result.forced_turn?'relay.json':'direct.json'),JSON.stringify(result,null,2));
  for(const observation of result.request_observations){
   assert.equal(observation.visible_error,null,'No unresolved user-facing timeout after acceptance');
   assert.equal(observation.requests.filter(r=>r.phase==='body'&&r.status===200).length,0,'Successful responses remain readable during rendering');
  }
  if(result.forced_turn){const direct=JSON.parse(fs.readFileSync(path.join(out,'direct.json')));assert.equal(direct.sha,result.sha);assert.equal(direct.origin,origin);fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify({...result,checks:{...direct.checks,...result.checks}},null,2));}
 }catch(e){await diagnostics(e);throw e}finally{
  if(event&&users[0])await users[0].api('/events/'+event.id+'/state/cancel',{}).catch(()=>{});
  for(const u of activeUsers){if(u.api&&!u.reusable)await u.api('/me',undefined,'DELETE').catch(()=>{});if(u.api&&u.reusable)await u.api('/auth/logout',{}).catch(()=>{});await u.context.close();}
  await browser.close();
 }
}
main().catch(e=>{console.error('Acceptance failed at '+stage+': '+safeText(e.message,sensitive));process.exitCode=1;browser?.close().catch(()=>{})});
