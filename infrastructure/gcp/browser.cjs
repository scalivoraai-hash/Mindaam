/* GCP staging only: actual HTTPS/WebRTC, synthetic capture, no database fixtures. */
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const {chromium}=require(process.env.QA_NODE_MODULES+'/playwright');
const release=JSON.parse(fs.readFileSync('deployment-result.json'));
assert.equal(release.environment,'staging');
const origin=release.origin;assert.match(origin,/^https:\/\/[a-z0-9.-]+\.run\.app$/);
const out='gcp-evidence';fs.mkdirSync(out,{recursive:true});
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
 const page=await context.newPage(),states=[],logs=[],inputs=[];
 page.on('requestfailed',request=>{if(/\/api\/media\/[^/]+\/token$/.test(new URL(request.url()).pathname))console.log('MEDIA GRANT REQUEST FAILED',index,request.failure()?.errorText)});
 page.on('pageerror',e=>{errors.push({city,index,error:e.message,stack:e.stack});console.log('Browser error',city,index,e.stack)});page.on('console',m=>{if(m.text().startsWith('[media]')||m.text().startsWith('[rtc]')||m.text().startsWith('[rtc-call]')||(['warning','error'].includes(m.type())&&!/token=|access_token|Bearer/i.test(m.text()))){logs.push(m.text());console.log(city,index,m.text())}});
 page.on('websocket',ws=>{if(ws.url().endsWith('/api/realtime')){ws.on('framesent',frame=>{try{const d=JSON.parse(frame.payload.toString());if(d.type==='input'){inputs.push({at:Date.now(),...d});if(inputs.length>120)inputs.shift()}}catch{}});ws.on('framereceived',frame=>{try{const d=JSON.parse(frame.payload.toString());if(d.type==='state'){states.push(d);if(states.length>80)states.shift()}}catch{}})}});
 const api=async(route,data,method=data===undefined?'GET':'POST')=>{const res=await context.request.fetch(origin+'/api'+route,{method,data,headers:{Origin:origin,'X-Pulse-Client':'web'}});if(!res.ok())throw Error(route+' '+res.status()+' '+await res.text());return res.json()};
 const name='gcpqa'+Date.now().toString(36)+index; const password=crypto.randomBytes(24).toString('base64url')+'!aA1';
 const registered=await api('/auth/register',{email:name+'@example.test',username:name,password:password,confirm_password:password,adult:true,accepted_terms:true,accepted_privacy:true});
 await api('/onboarding',{city,interests:['music'],avatar:{color:index?'#41a8b8':'#ed945d'},privacy:'City Mode',location_consent:false,analytics_consent:false});
 await api('/auth/logout',{});await api('/auth/login',{identifier:name,password:password});const me=await api('/me');assert.equal(me.id,registered.user.id,'Staging session identity');assert.equal(me.onboarded,true,'Onboarding persisted before browser entry');
 await page.goto(origin);await page.locator('.welcome-home').waitFor({timeout:60000});try{await page.locator('.destination-card.is-owned').first().click()}catch(e){console.log('Entry page',await page.locator('body').innerText());await page.screenshot({path:path.join(out,'entry-'+index+'.jpg'),timeout:6000}).catch(()=>{});fs.writeFileSync(path.join(out,'entry-'+index+'.txt'),await page.locator('body').innerText());console.log('Entry errors',errors);throw e}await page.locator('.world-access-modal').getByRole('button',{name:/^Enter /}).click();
 await page.locator('.world-playing').waitFor();try{await until(()=>states.at(-1)?.city===city,'World state '+city,60000)}catch(e){console.log('Entry diagnostics',JSON.stringify({city,index,states:states.map(s=>({city:s.city,type:s.type})),errors,body:await page.locator('body').innerText({timeout:5000}).catch(()=>'(page unresponsive)')}));throw e}
 return {context,page,api,id:registered.user.id,states,logs,inputs,touch};
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
async function main(){
 const health=await fetch(origin+'/api/health').then(r=>r.json());assert.equal(health.environment,'staging');assert.equal(health.status,'ready');
 // 20 seconds of a sine wave, consumed by Chromium's fake microphone.
 const samples=48000*20,wav=Buffer.alloc(44+samples*2);wav.write('RIFF');wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(48000,24);wav.writeUInt32LE(96000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(samples*2,40);for(let i=0;i<samples;i++)wav.writeInt16LE(Math.round(8000*Math.sin(2*Math.PI*440*i/48000)),44+i*2);fs.writeFileSync('/tmp/mindaam-tone.wav',wav);
 browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--auto-select-desktop-capture-source=Entire screen','--use-file-for-fake-audio-capture=/tmp/mindaam-tone.wav','--disable-background-timer-throttling']});
 const users=[],checks={},result={sha:release.sha,origin,checks,synthetic_capture:true,forced_turn:process.env.QA_FORCE_TURN==='1'};let event;
 try{
  const a=await user('milton-keynes',0);users.push(a);const b=await user('milton-keynes',1);users.push(b);
  assert.equal(await a.page.evaluate(()=>window.__gcpPeers.length),0,'Ordinary world must not create media connections');
  await a.api('/social/'+b.id+'/friend',{});await b.api('/social/'+a.id+'/accept',{});
  checks.browser=true;
  // Public auditorium entry places real users together using application APIs.
  event=await a.api('/events',{title:'GCP staging acceptance '+Date.now(),description:'Automated staging QA, synthetic devices. Not a public customer event.',city:'milton-keynes',starts_at:Date.now()/1000,communication_mode:'liveface',venue_experience_type:'auditorium',event_type:'Public Talk'});
  await a.api('/events/'+event.id+'/state/start',{});await b.api('/events/'+event.id+'/join',{});await b.api('/events/'+event.id+'/venue/enter',{});
  await until(()=>peer(a,b.id)&&peer(b,a.id),'Mutual realtime presence',60000);
  const start=position(a);await move(a,.4,0);await until(()=>Math.hypot(position(a).x-start.x,position(a).z-start.z)>.05,'Movement');await move(a,0,0);
  await until(()=>Math.abs(peer(b,a.id).x-position(a).x)<.5,'Remote movement');checks.multiplayer=true;
  await controls(a,/Reconnect|Join LiveFace/);await until(()=>a.page.locator('.live-dock.is-connected').count(),'Host connection');
  assert.equal(await a.page.getByRole('button',{name:'Camera On',exact:true}).count(),1);assert.equal(await a.page.getByRole('button',{name:'Unmute',exact:true}).count(),1);
  assert.equal(await sentTracks(b),0,'Audience publishes no camera or microphone');
  await controls(a,/Camera On/);await controls(a,/Unmute/);await controls(b,/Expand/);
  await video(b,a.id);checks.video=true;await audio(b,a.id);checks.voice=true;
  const c=await user('milton-keynes',2);users.push(c);await c.api('/events/'+event.id+'/join',{});await c.api('/events/'+event.id+'/venue/enter',{});await controls(c,/Expand/);await video(c,a.id);await audio(c,a.id);assert.equal(await sentTracks(c),0);
  await a.api('/events/'+event.id+'/people/'+b.id+'/speaker',{});await until(()=>b.page.getByRole('button',{name:'Camera On',exact:true}).count(),'Stage promotion');await controls(b,/Camera On/);await controls(b,/Unmute/);await controls(a,/Expand/);await video(a,b.id);await audio(a,b.id);
  await a.api('/events/'+event.id+'/people/'+b.id+'/audience',{});await until(async()=>await sentTracks(b)===0,'Revoked audience publishing');checks.event_media=true;
  await a.page.locator('.event-share-controls').getByRole('button',{name:'Share screen',exact:true}).click();
  await until(()=>c.page.locator('.presentation-sources video[data-track-source="screen_share"]').evaluateAll(es=>es.some(e=>e.videoWidth>0&&e.readyState>=2)),'Actual decoded screen');checks.screen_share=true;
  await audio(c,a.id);await a.page.getByRole('button',{name:'Stop sharing',exact:true}).click();
  for(const size of [{width:390,height:844},{width:820,height:1180},{width:1440,height:900}]){await c.page.setViewportSize(size);await video(c,a.id);assert.ok(await c.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));await screenshot(c,'viewport-'+size.width+(result.forced_turn?'-turn':''));}
  assert.ok(await c.page.locator('.remote-tile video').evaluateAll(es=>es.every(e=>e.videoHeight<=720)),'Startup resolution cap');checks.startup_policy=true;
  if(result.forced_turn){await relay(a);await relay(c);checks.turn_tls=true;}
  assert.equal(errors.length,0,'No uncaught browser errors');
  fs.writeFileSync(path.join(out,result.forced_turn?'relay.json':'direct.json'),JSON.stringify(result,null,2));
  if(result.forced_turn){const direct=JSON.parse(fs.readFileSync(path.join(out,'direct.json')));assert.equal(direct.sha,result.sha);assert.equal(direct.origin,origin);fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify(result,null,2));}
 }finally{
  if(event&&users[0])await users[0].api('/events/'+event.id+'/state/end',{}).catch(()=>{});
  for(const u of users){await u.api('/me',undefined,'DELETE').catch(()=>{});await u.context.close();}
  await browser.close();
 }
}
main().catch(e=>{console.error(e.message);process.exitCode=1;browser?.close().catch(()=>{})});
