/* GCP staging only: actual HTTPS/WebRTC, synthetic capture, no database fixtures. */
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const {chromium}=require(process.env.QA_NODE_MODULES+'/playwright');
const release=JSON.parse(fs.readFileSync('deployment-result.json'));
assert.equal(release.environment,'staging');
const origin=release.origin;assert.match(origin,/^https:\/\/[a-z0-9.-]+\.run\.app$/);
const out='gcp-evidence';fs.mkdirSync(out,{recursive:true});
const {required,safeText,safeUrl,validatePolicy}=require('./browser-contract.cjs');
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
 const page=await context.newPage(),states=[],logs=[],inputs=[],failures=[],grants=[];
 const u={context,page,states,logs,inputs,failures,grants,touch,index};activeUsers.push(u);
 page.setDefaultTimeout(60000);page.setDefaultNavigationTimeout(90000);
 page.on('response',async response=>{const url=safeUrl(response.url());if(response.status()>=400)failures.push({url,status:response.status()});if(/\/api\/media\/[^/]+\/token$/.test(new URL(url).pathname)&&response.ok()){try{const g=await response.json();sensitive.push(g.token);grants.push({host:new URL(g.url).hostname,policy:g.media_policy,can_speak:g.can_speak})}catch{}}if(failures.length>80)failures.shift()});
 page.on('requestfailed',request=>{failures.push({url:safeUrl(request.url()),error:safeText(request.failure()?.errorText,sensitive)});if(failures.length>80)failures.shift()});
 page.on('pageerror',e=>errors.push({index,error:safeText(e.message,sensitive)}));
 page.on('console',m=>{if(['warning','error'].includes(m.type())){logs.push(safeText(m.text(),sensitive));if(logs.length>80)logs.shift()}});
 page.on('websocket',ws=>{if(ws.url().endsWith('/api/realtime')){ws.on('framesent',frame=>{try{const d=JSON.parse(frame.payload.toString());if(d.type==='input'){inputs.push({at:Date.now(),...d});if(inputs.length>120)inputs.shift()}}catch{}});ws.on('framereceived',frame=>{try{const d=JSON.parse(frame.payload.toString());if(d.type==='state'){states.push(d);if(states.length>80)states.shift()}}catch{}})}});
 const api=async(route,data,method=data===undefined?'GET':'POST')=>{const res=await context.request.fetch(origin+'/api'+route,{method,data,headers:{Origin:origin,'X-Pulse-Client':'web'}});if(!res.ok())throw Error('API '+safeUrl(origin+'/api'+route)+' HTTP '+res.status());return res.json()};
 let name='gcpqa'+Date.now().toString(36)+index;const reusable=index===0&&!!process.env.QA_STAGING_HOST_IDENTIFIER;const password=reusable?process.env.QA_STAGING_HOST_PASSWORD:crypto.randomBytes(24).toString('base64url')+'!aA1';assert.ok(password,'Reusable staging host password is required');u.reusable=reusable;
 sensitive.push(password);u.api=api;stage='signup-'+index;
 await page.goto(origin,{waitUntil:'domcontentloaded'});
 if(reusable){
 sensitive.push(process.env.QA_STAGING_HOST_IDENTIFIER);await page.getByLabel('Email or username',{exact:true}).fill(process.env.QA_STAGING_HOST_IDENTIFIER);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Enter Mindaam',exact:true}).click();await until(async()=>{try{return (await api('/me')).onboarded}catch{return false}},'Funded host login');const account=await api('/me');u.id=account.id;name=account.username;assert.equal(account.onboarded,true);
 }else{
 await page.getByRole('button',{name:'New here? Create an account',exact:true}).click();
 await page.getByLabel('Username',{exact:true}).fill(name);
 await page.getByLabel('Email address',{exact:true}).fill(name+'@example.test');
 await page.getByLabel('Password',{exact:true}).fill(password);await page.getByLabel('Confirm password',{exact:true}).fill(password);
 for(const field of ['adult','terms','privacy'])await page.locator('input[name="'+field+'"]').check();
 await page.getByRole('button',{name:'Create your account',exact:true}).click();
 await page.getByRole('group',{name:'Choose your first free world'}).waitFor();
 const registered=await api('/me');u.id=registered.id;assert.equal(registered.onboarded,false);
 stage='onboarding-'+index;
 await page.getByRole('group',{name:'Choose your first free world'}).locator('select[name="city"]').selectOption(city);
 await page.getByRole('checkbox',{name:/as Starter World 1 of 4/}).check();
 await page.getByRole('checkbox',{name:'Music',exact:true}).check();
 await page.getByRole('button',{name:'Let’s explore',exact:true}).click();
 await page.getByRole('heading',{name:'Welcome back, '+name+'.',exact:true}).waitFor();
 assert.equal((await api('/me')).onboarded,true);
 }
 stage='login-session-'+index;
 await api('/auth/logout',{});await page.reload({waitUntil:'domcontentloaded'});
 await page.getByLabel('Email or username',{exact:true}).fill(name);await page.getByLabel('Password',{exact:true}).fill(password);
 await page.getByRole('button',{name:'Enter Mindaam',exact:true}).click();
 await page.getByRole('heading',{name:'Welcome back, '+name+'.',exact:true}).waitFor();
 await page.reload({waitUntil:'domcontentloaded'});
 await page.getByRole('heading',{name:'Welcome back, '+name+'.',exact:true}).waitFor();
 assert.equal((await api('/me')).id,u.id,'Browser cookie session persists across reload');
 stage='world-entry-'+index;
 const cities=await api('/cities'),destination=cities.find(c=>c.id===city);assert.ok(destination);
 await page.getByRole('region',{name:'Explore worlds'}).getByRole('button').filter({hasText:destination.name}).first().click();
 await page.getByRole('dialog',{name:'Choose a world'}).getByRole('button',{name:'Enter '+destination.name,exact:true}).click();
 await page.locator('.world-playing').waitFor();
 await page.locator('.world-canvas[data-ready="true"]').waitFor({timeout:90000});
 await until(()=>states.at(-1)?.city===city,'Authenticated realtime world state '+city,60000);
 u.username=name;return u;
}
async function settled(users){
 await Promise.all(users.map(u=>move(u,0,0)));let stableSince=Date.now(),previous=JSON.stringify(users.map(position));
 await until(()=>{const next=JSON.stringify(users.map(position));if(next!==previous){previous=next;stableSince=Date.now()}return Date.now()-stableSince>1800&&users.every(u=>(u.states.at(-1)?.server_time||0)*1000>Date.now()-1500)},'Stopped positions',12000);
 return users.map(position);
}
const position=u=>{const p=u.states.at(-1)?.position;return p&&{x:p.x,z:p.z,zone:p.zone_id}};
const peer=(u,id)=>u.states.at(-1)?.players.find(p=>p.id===id);
async function controls(u,which){const button=u.page.locator('.live-dock').getByRole('button',{name:which}).last();if(!(await button.isVisible())&&await u.page.getByRole('button',{name:'More media controls',exact:true}).count())await u.page.getByRole('button',{name:'More media controls',exact:true}).click();if(u.touch)await button.tap();else await button.click()}
async function video(u,id){return until(()=>u.page.locator('.remote-tile[data-peer-id="'+id+'"] video:not([hidden])').evaluateAll(v=>v.some(el=>el.videoWidth>0&&el.readyState>=2)),'Decoded remote video')}
async function audio(u,id){const enable=u.page.getByRole('button',{name:/Audio is ready. Tap to listen/});if(await enable.count())await enable.click();return until(()=>u.page.locator('.remote-tile[data-peer-id="'+id+'"] audio').evaluateAll(async elements=>{
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
  const data={stage,error:safeText(error.message,sensitive),url:safeUrl(u.page.url()),console:u.logs,network:u.failures,errors};
  try{data.title=safeText(await u.page.title(),sensitive);data.body=safeText(await u.page.locator('body').innerText({timeout:4000}),sensitive);
   data.state=await u.page.evaluate(()=>({world:!!document.querySelector('.world-playing'),ready:document.querySelector('.world-canvas')?.getAttribute('data-ready'),welcome:!!document.querySelector('.welcome-home'),onboarding:!!document.querySelector('.onboarding'),media:window.__gcpPeers.map(p=>({connection:p.connectionState,ice:p.iceConnectionState,senders:p.getSenders().filter(s=>s.track?.readyState==='live').length}))}));
   const me=await u.api?.('/me');if(me)data.user={id:me.id,onboarded:me.onboarded,city:me.city};
  }catch{data.collection_incomplete=true}
  await u.page.screenshot({path:prefix+'.jpg',type:'jpeg',quality:65,timeout:5000,mask:[u.page.locator('input,textarea,pre,code')]}).catch(()=>{});
  fs.writeFileSync(prefix+'.json',JSON.stringify(data,null,2));
 }
 fs.writeFileSync(path.join(out,mode+'-failure.json'),JSON.stringify({stage,error:safeText(error.message,sensitive)},null,2));
}

async function main(){
 const health=await until(async()=>{
  try{
   const response=await fetch(origin+'/api/health',{signal:AbortSignal.timeout(5000)});
   if(!response.ok())return false;
   if(!(response.headers.get('content-type')||'').toLowerCase().includes('application/json'))return false;
   const value=await response.json();
   return value?.environment==='staging'&&value?.status==='ready'?value:false;
  }catch{return false}
 },'Staging health JSON',120000);
 assert.equal(health.environment,'staging');assert.equal(health.status,'ready');
 // 20 seconds of a sine wave, consumed by Chromium's fake microphone.
 const samples=48000*20,wav=Buffer.alloc(44+samples*2);wav.write('RIFF');wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(48000,24);wav.writeUInt32LE(96000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(samples*2,40);for(let i=0;i<samples;i++)wav.writeInt16LE(Math.round(8000*Math.sin(2*Math.PI*440*i/48000)),44+i*2);fs.writeFileSync('/tmp/mindaam-tone.wav',wav);
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--auto-select-desktop-capture-source=Entire screen','--use-file-for-fake-audio-capture=/tmp/mindaam-tone.wav','--disable-background-timer-throttling']});
 const users=[],checks={},result={sha:release.sha,origin,checks,synthetic_capture:true,forced_turn:process.env.QA_FORCE_TURN==='1'};let event;
 try{
  const a=await user('milton-keynes',0);users.push(a);const b=await user('milton-keynes',1);users.push(b);
  stage='ordinary-world';
  assert.equal(await a.page.evaluate(()=>window.__gcpPeers.length),0,'Ordinary world must not create media connections');
  await a.api('/social/'+b.id+'/friend',{});await b.api('/social/'+a.id+'/accept',{});
  for(const u of [a,b]){assert.equal(await u.page.evaluate(()=>window.__gcpPeers.length),0);assert.ok((await u.api('/friends')).some(p=>p.friend&&p.id===(u===a?b.id:a.id)))}
  await a.page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'PEOPLE',exact:true}).click();
  await a.page.getByRole('heading',{name:'Your people',exact:true}).waitFor();await a.page.getByRole('tab',{name:'Friends',exact:true}).click();
  stage='profiles';await b.api('/me/profile',{display_name:'Staging profile check',bio:'Automated staging acceptance',links:{instagram:{url:'@mindaamqa',visible:true},facebook:{url:'mindaamqa',visible:false}}},'PUT');
  await a.page.locator('.friend-card').filter({hasText:b.username}).getByRole('button',{name:'View profile',exact:true}).click();const profile=a.page.getByRole('dialog',{name:'Player profile',exact:true});await profile.getByRole('heading',{name:'Staging profile check',exact:true}).waitFor();assert.equal(await profile.locator('a[href*="facebook.com"]').count(),0);await profile.getByRole('button',{name:'Follow',exact:true}).click();await profile.getByRole('button',{name:'Unfollow',exact:true}).waitFor();await profile.getByRole('button',{name:'Avatar',exact:true}).click();await profile.locator('.avatar-preview canvas').waitFor();assert.equal(await profile.getByText('3D preview is unavailable in this browser.',{exact:false}).count(),0);await profile.getByRole('button',{name:'Close profile',exact:true}).click();checks.profiles=true;checks.avatar_rendering=true;
  await a.page.getByRole('button',{name:'Close panel',exact:true}).click();
  for(const key of ['browser','signup','login','onboarding','session_persistence','world_entry','friends','no_world_media'])checks[key]=true;
  stage='events-auditorium';
  // Public auditorium entry places real users together using application APIs.
  event=await a.api('/events',{title:'GCP staging acceptance '+Date.now(),description:'Automated staging QA, synthetic devices. Not a public customer event.',city:'milton-keynes',starts_at:Date.now()/1000,communication_mode:'liveface',venue_experience_type:'auditorium',event_type:'Public Talk'});
  const catalogue=await a.api('/venue-rentals/milton-keynes'),cost=catalogue.prices?.['1'];
  const maxCost=Number(process.env.QA_STAGING_MAX_RESERVATION_PC||0);
  assert.ok(a.reusable&&catalogue.enabled&&Number.isInteger(cost)&&cost>0&&cost<=maxCost&&catalogue.purchased_credits>=cost,'Paid venue acceptance requires a dedicated purchased-credit staging host and an explicit per-reservation PC limit. No test credits are fabricated.');
  const reservation=await a.api('/events/'+event.id+'/venue/booking',{request_id:crypto.randomUUID(),hours:1,starts_at:Date.now()/1000,expected_cost:cost});assert.equal(reservation.cost,cost);checks.venue_booking=true;
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
  await until(()=>b.page.getByRole('button',{name:'Camera On',exact:true}).count().then(n=>n===0),'Audience camera control removed');stage='screen-sharing';
  await a.page.locator('.event-share-controls').getByRole('button',{name:'Share screen',exact:true}).click();
  await until(()=>c.page.locator('.presentation-sources video[data-track-source="screen_share"]').evaluateAll(es=>es.some(e=>e.videoWidth>0&&e.readyState>=2)),'Actual decoded screen');checks.screen_share=true;
  await audio(c,a.id);await a.page.getByRole('button',{name:'Stop sharing',exact:true}).click();
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
  for(const key of required)assert.equal(checks[key],true,'Missing acceptance '+key);
  assert.equal(errors.length,0,'No uncaught browser errors');
  fs.writeFileSync(path.join(out,result.forced_turn?'relay.json':'direct.json'),JSON.stringify(result,null,2));
  if(result.forced_turn){const direct=JSON.parse(fs.readFileSync(path.join(out,'direct.json')));assert.equal(direct.sha,result.sha);assert.equal(direct.origin,origin);fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify(result,null,2));}
 }catch(e){await diagnostics(e);throw e}finally{
  if(event&&users[0])await users[0].api('/events/'+event.id+'/state/cancel',{}).catch(()=>{});
  for(const u of activeUsers){if(u.api&&!u.reusable)await u.api('/me',undefined,'DELETE').catch(()=>{});if(u.api&&u.reusable)await u.api('/auth/logout',{}).catch(()=>{});await u.context.close();}
  await browser.close();
 }
}
main().catch(e=>{console.error('Acceptance failed at '+stage+': '+safeText(e.message,sensitive));process.exitCode=1;browser?.close().catch(()=>{})});
