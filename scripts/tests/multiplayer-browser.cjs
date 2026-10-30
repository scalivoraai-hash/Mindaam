/* Preserved Arena regression runs opt in only in disposable local databases; public default-closed behavior is tested separately. */
/* Real production Next build + existing API + local LiveKit, isolated user contexts.
 * Synthetic camera and sine-wave microphone exercise WebRTC; no physical-device claim. */
const {spawn,execFileSync}=require('child_process'),fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const {chromium}=require((process.env.QA_NODE_MODULES||process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES)+'/playwright');
const root=path.resolve(__dirname,'../..'),out=process.env.QA_OUTPUT||'/tmp/mylil-multiplayer-evidence';fs.mkdirSync(out,{recursive:true});
const python=process.env.QA_PYTHON||'/tmp/mylil-visual-testenv/bin/python',origin='http://127.0.0.1:3000';
const env={...process.env,APP_ENV:'local',MINDAAM_GRAND_ARENA_ENABLED:'true',PUBLIC_ORIGIN:origin,DATABASE_URL:'sqlite:////tmp/mylil-multi-'+Date.now()+'.db',LIVEKIT_URL:'ws://127.0.0.1:7880',LIVEKIT_API_KEY:'local-browser-qa',LIVEKIT_API_SECRET:crypto.randomBytes(32).toString('hex')};
const skipMedia=process.env.QA_SKIP_MEDIA==='1',mapRenderer=process.env.QA_RENDERER==='map',mixedRenderer=process.env.QA_RENDERER==='mixed';const children=[],results=[],errors=[];let browser;
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const fixture=(action,data={})=>JSON.parse(execFileSync(python,['-m','scripts.tests.multiplayer_fixture',action,JSON.stringify(data)],{cwd:root,env,encoding:'utf8'}));
function start(bin,args,log){const fd=fs.openSync(path.join(out,log),'w'),p=spawn(bin,args,{cwd:root,env,stdio:['ignore',fd,fd]});children.push(p);return p}
async function until(fn,label,timeout=25000){const end=Date.now()+timeout;let error;while(Date.now()<end){try{const value=await fn();if(value)return value}catch(e){error=e}await wait(200)}throw Error(label+' timed out'+(error?' · '+error.message:''))}
async function ready(url){return until(async()=>{try{return(await fetch(url,{signal:AbortSignal.timeout(3000)})).ok}catch{return false}},'Ready '+url,90000)}
async function reserveArena(u,event){
 const catalog=await u.api('/venue-rentals/'+event.city),cost=catalog.prices['1'];
 assert.ok(catalog.enabled&&cost>0,'Local venue catalogue must be enabled');
 fixture('venue_funds',{city:event.city,users:[u.id],event_id:event.id,cost});
 const receipt=await u.api('/events/'+event.id+'/venue/booking',{request_id:crypto.randomUUID(),hours:1,expected_cost:cost,starts_at:Date.now()/1000});
 assert.equal(receipt.cost,cost);return receipt;
}
async function user(city,index){
 const touch=index===2;const context=await browser.newContext({viewport:touch?{width:390,height:844}:{width:1100,height:760},isMobile:touch,hasTouch:touch,permissions:['camera','microphone']});
 if(mixedRenderer)await context.addInitScript(({observer})=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){if((kind==='webgl'||kind==='webgl2')&&(!observer||!document.querySelector('.world-playing')))return null;return get.call(this,kind,...args)}},{observer:index===1});
 await context.addInitScript(()=>{
  const Native=window.WebSocket;window.WebSocket=new Proxy(Native,{construct(Target,args){const socket=Reflect.construct(Target,args);socket.addEventListener('message',event=>{try{const d=JSON.parse(event.data);if(['state','motion'].includes(d.type)&&d.position&&(d.position.last_move||0)>=(window.__qaMotion?.last_move||0)){window.__qaMotion=d.position;window.dispatchEvent(new CustomEvent('qa-motion',{detail:d.position}))}}catch{}});return socket}});
 });
 await context.addInitScript(()=>{window.__qaFrames=[];window.__qaMedia=[];window.addEventListener('pulse-avatar-anchors',e=>{window.__qaAnchors=e.detail;window.__qaAnchorViewport={width:innerWidth,height:innerHeight}});window.addEventListener('pulse-media-status',e=>window.__qaMedia.push(e.detail));});
 await context.addInitScript(()=>{
  window.__qaRtc=[];const Native=window.RTCPeerConnection;let id=0;
  window.RTCPeerConnection=new Proxy(Native,{construct(Target,args){const pc=Reflect.construct(Target,args),key=++id;const record=()=>{const state={id:key,at:Date.now(),connection:pc.connectionState,ice:pc.iceConnectionState,signaling:pc.signalingState,visibility:document.visibilityState};window.__qaRtc.push(state);if(window.__qaRtc.length>120)window.__qaRtc.shift();console.log('[rtc]',JSON.stringify(state))};for(const name of ['connectionstatechange','iceconnectionstatechange','signalingstatechange'])pc.addEventListener(name,record);record();console.log('[rtc-call]',JSON.stringify({id:key,method:'constructor',stack:new Error().stack}));for(const method of ['createOffer','createAnswer','setLocalDescription','setRemoteDescription','close']){const original=pc[method];pc[method]=function(...args){console.log('[rtc-call]',JSON.stringify({id:key,method,at:Date.now()}));return original.apply(this,args)}}return pc}});
 });
 // Capture the failing media transition without changing rendering or deadlines.
 if(process.env.QA_CHECK==='media')await context.addInitScript(()=>{
  window.__qaGpu=[];window.__qaRenderEvents=[];let sequence=0;
  const contexts=new WeakMap();
  for(const name of ['fenceSync','clientWaitSync','drawElements','drawArrays','createProgram','deleteProgram','createTexture','deleteTexture','bufferData','texImage2D','texSubImage2D']){
   const proto=WebGL2RenderingContext.prototype,original=proto[name];
   proto[name]=function(...args){let state=contexts.get(this);if(!state){state={id:++sequence,calls:{},waits:{},slow:[],last:0};contexts.set(this,state);window.__qaGpu.push(state);this.canvas.addEventListener('webglcontextlost',()=>state.lost=true)}const start=performance.now(),value=original.apply(this,args),elapsed=performance.now()-start;state.calls[name]=(state.calls[name]||0)+1;state.last=performance.now();if(name==='clientWaitSync')state.waits[value]=(state.waits[value]||0)+1;if(elapsed>50){state.slow.push({name,ms:elapsed,at:start});if(state.slow.length>30)state.slow.shift()}return value};
  }
  for(const event of ['pulse-world-ready','pulse-stage-media'])window.addEventListener(event,e=>{window.__qaRenderEvents.push({event,at:performance.now(),ready:e.detail===true,source:e.detail?.source});if(window.__qaRenderEvents.length>30)window.__qaRenderEvents.shift()});
 });
 const page=await context.newPage(),states=[],logs=[],inputs=[];
 page.on('requestfailed',request=>{if(/\/api\/media\/[^/]+\/token$/.test(new URL(request.url()).pathname))console.log('MEDIA GRANT REQUEST FAILED',index,request.failure()?.errorText)});
 page.on('pageerror',e=>{errors.push({city,index,error:e.message,stack:e.stack});console.log('Browser error',city,index,e.stack)});page.on('console',m=>{if(m.text().startsWith('[media]')||m.text().startsWith('[rtc]')||m.text().startsWith('[rtc-call]')||(['warning','error'].includes(m.type())&&!/token=|access_token|Bearer/i.test(m.text()))){logs.push(m.text());console.log(city,index,m.text())}});
 page.on('websocket',ws=>{if(ws.url().endsWith('/api/realtime')){ws.on('framesent',frame=>{try{const d=JSON.parse(frame.payload.toString());if(d.type==='input'){inputs.push({at:Date.now(),...d});if(inputs.length>120)inputs.shift()}}catch{}});ws.on('framereceived',frame=>{try{const d=JSON.parse(frame.payload.toString());if(d.type==='state'){states.push(d);if(states.length>80)states.shift()}}catch{}})}});
 const api=async(route,data,method=data===undefined?'GET':'POST')=>{const res=await context.request.fetch(origin+'/api'+route,{method,data,headers:{Origin:origin,'X-Pulse-Client':'web'}});if(!res.ok())throw Error(route+' '+res.status()+' '+await res.text());return res.json()};
 const name='qa'+Date.now().toString(36)+index;
 const registered=await api('/auth/register',{email:name+'@example.test',username:name,password:'LocalBrowserQA2026!pass',confirm_password:'LocalBrowserQA2026!pass',adult:true,accepted_terms:true,accepted_privacy:true});
 await api('/onboarding',{city,interests:['music'],avatar:{color:index?'#41a8b8':'#ed945d'},privacy:'City Mode',location_consent:false,analytics_consent:false});
 await api('/auth/logout',{});await api('/auth/login',{identifier:name,password:'LocalBrowserQA2026!pass'});const me=await api('/me');assert.equal(me.id,registered.user.id,'Fixture session identity');assert.equal(me.onboarded,true,'Onboarding persisted before browser entry');
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
async function runCity(city){
 console.log('Testing',city);const a=await user(city,0),b=await user(city,1),users=[a,b],evidence={city,renderer:mapRenderer?'existing-map-fallback':mixedRenderer?'3d-observer-map-driver':'webgl',checks:{}};
 const check=(key,value)=>{assert.ok(value,city+' '+key);evidence.checks[key]=true;console.log(city,key,'PASS')};
 try{
  const placedWalk=fixture('place',{city,users:users.map(u=>u.id)});const direction=placedWalk.direction;await wait(1600);
  check('mutual_presence',!!peer(a,b.id)&&!!peer(b,a.id));if(mixedRenderer)check('observer_webgl',await b.page.locator('.world-canvas canvas').count()>0&&await b.page.locator('.world-fallback').count()===0);
  const start=position(a);await Promise.all(users.map(u=>move(u,direction[0]*.6,direction[1]*.6)));await until(()=>Math.hypot(position(a).x-start.x,position(a).z-start.z)>.2,'Walk on traversable road',8000);await Promise.all(users.map(u=>move(u,0,0)));await wait(700);
  check('walk_remote_updates',Math.hypot(position(a).x-start.x,position(a).z-start.z)>.05&&!!peer(b,a.id));
  for(const u of users)await u.page.getByRole('button',{name:'run',exact:true}).click();
  await Promise.all(users.map(u=>move(u,-direction[0]*.6,-direction[1]*.6)));await until(()=>peer(b,a.id)?.mode==='run','Remote running mode',8000);await Promise.all(users.map(u=>move(u,0,0)));await wait(400);
  check('run_remote_mode',b.states.some(s=>s.players.some(p=>p.id===a.id&&p.mode==='run')));
  for(const u of users)await u.page.getByRole('button',{name:'walk',exact:true}).click();
  if(!skipMedia){
  fixture('place',{city,users:users.map(u=>u.id)});await until(()=>Math.hypot(position(a).x-position(b).x,position(a).z-position(b).z)<3,'Together before call');
  const before=await settled(users);evidence.callBefore=before;const invitation=await a.api('/media/request',{target_id:b.id,kind:'liveface'});await b.api('/media/'+invitation.id+'/accept',{});
  await until(()=>a.page.locator('.live-dock .media-ready').count(),'Call controls');
  await Promise.all(users.map(u=>controls(u,/Join LiveFace/)));await until(async()=>(await Promise.all(users.map(u=>u.page.locator('.live-dock.is-connected').count()))).every(n=>n===1),'Joined with cameras off');check('camera_off_on_join',await Promise.all(users.map(u=>u.page.getByRole('button',{name:'Camera On',exact:true}).count())).then(xs=>xs.every(n=>n===1)));await Promise.all(users.map(u=>controls(u,/Camera On/)));await Promise.all(users.map(u=>controls(u,/Expand/)));
  await Promise.all([video(a,b.id),video(b,a.id),audio(a,b.id),audio(b,a.id)]);
  check('two_way_video_audio',true);evidence.callAfter=users.map(position);check('can_we_talk_connected_state',await a.page.locator('.quick-social').getByRole('button',{name:'✓ Connected',exact:true}).isDisabled());check('join_no_position_change',users.every((u,i)=>JSON.stringify(position(u))===JSON.stringify(before[i])));
  await Promise.all(users.map(u=>move(u,.25,-.25)));await wait(900);await Promise.all(users.map(u=>move(u,0,0)));await Promise.all([audio(a,b.id),video(b,a.id)]);check('walk_during_call',true);
  for(const u of users)await u.page.getByRole('button',{name:'run',exact:true}).click();
  await Promise.all(users.map(u=>move(u,-.25,.25)));await wait(900);await Promise.all(users.map(u=>move(u,0,0)));await audio(a,b.id);check('run_during_call',true);
  for(const u of users)await u.page.getByRole('button',{name:'walk',exact:true}).click();
  await settled(users);const stationary=position(a);evidence.layoutBefore=stationary;evidence.layoutStarted=Date.now();
  for(const control of [/Full Screen/,/Exit Full Screen/,/Minimise/,/Expand/]){await controls(a,control);await wait(400);if(control.source.includes('Minimise'))await audio(a,b.id);else await video(a,b.id)}
  evidence.layoutAfter=position(a);check('layout_preserves_position',JSON.stringify(position(a))===JSON.stringify(stationary));await screenshot(a,city+'-call');
  await controls(a,/Leave & End/);await until(()=>!a.states.at(-1).media.some(s=>s.state==='accepted'),'Call end');
  }
  // Genuine one-click rental UI, socket driving, remote authoritative rendering.
  for(const [driver,observer,kind] of [[a,b,'car'],[a,b,'bike'],[b,a,'car'],[b,a,'bike']]){
   const placed=fixture('place',{city,users:users.map(u=>u.id),kind});await wait(1300);
   await driver.page.evaluate(id=>window.dispatchEvent(new CustomEvent('pulse-city-action',{detail:{kind:'rental',data:{id}}})),placed.asset);
   await driver.page.locator('.mobility-panel article').first().waitFor();const accept=driver.page.getByRole('button',{name:/Accept.*policy|I accept|Accept & continue/i});if(await accept.count())await accept.click();
   const card=driver.page.locator('.mobility-panel article').filter({has:driver.page.getByRole('button',{name:kind==='car'?'Rent & drive':'Rent & ride',exact:true})}).first();
   await card.getByRole('button',{name:kind==='car'?'Rent & drive':'Rent & ride',exact:true}).click();
   await until(()=>peer(observer,driver.id)?.vehicle?.kind===kind,'Remote '+kind);
   await move(driver,0,-1);await wait(950);await move(driver,0,1);await wait(600);await move(driver,0,0);
   check((driver===a?'':'reverse_')+kind+'_remote_vehicle_identity',peer(observer,driver.id)?.vehicle?.id===placed.asset);await screenshot(observer,city+'-'+kind+'-remote-'+(driver===a?'a':'b'));
   await driver.page.getByRole('button',{name:'Exit vehicle',exact:true}).click();await until(()=>peer(observer,driver.id)&&!peer(observer,driver.id).vehicle,'Remote exit');check((driver===a?'':'reverse_')+kind+'_exit',true);
  }
  async function busTest(){
  await until(()=>Date.now()%30000<2500,'Scheduled local boarding window',32000);
  const bus=fixture('bus',{city,users:users.map(u=>u.id)});await a.api('/growth/worlds/'+bus.destination+'/starter',{confirmed:true});await wait(1200);
  await a.page.evaluate(()=>window.dispatchEvent(new CustomEvent('pulse-city-action',{detail:{kind:'transit',data:{}}})));
  await until(()=>a.page.locator('.departure-board article').count(),'Departure board');
  // Match route through its legitimate destination label from the endpoint.
  const board=await a.api('/transit/board/'+city),entry=board.routes.find(r=>r.id===bus.route);
  const button=a.page.locator('.departure-board article').filter({hasText:entry.destination_name}).getByRole('button',{name:'Buy ticket & board',exact:true});const walletBefore=await a.api('/wallet');let submits=0;const countRequest=r=>{if(r.url().endsWith('/api/transit/board')&&r.method()==='POST')submits++};a.page.on('request',countRequest);await button.click();
  await until(()=>a.states.at(-1)?.journey,'Board acknowledged');check('bus_first_tap',submits===1);const walletAfter=await a.api('/wallet');check('bus_single_charge',walletAfter.transactions.filter(t=>t.kind==='bus_ticket_xp'&&!walletBefore.transactions.some(old=>old.id===t.id)).length===1&&walletAfter.transactions.find(t=>t.kind==='bus_ticket_xp'&&!walletBefore.transactions.some(old=>old.id===t.id)).amount===-entry.fare&&walletBefore.xp-walletAfter.xp===entry.fare&&walletBefore.credits===walletAfter.credits);a.page.off('request',countRequest);
  await until(()=>peer(b,a.id)?.vehicle?.kind==='bus','Remote bus passenger');check('bus_remote_passenger',true);await screenshot(b,city+'-bus');
  console.log(city,'Travelling to destination');await until(()=>a.states.at(-1)?.journey?.arrived,'Destination arrival',85000);await a.page.getByRole('button',{name:'Get off',exact:true}).click();await until(()=>!a.states.at(-1)?.journey&&a.states.at(-1)?.city===bus.destination,'Bus exit');check('bus_destination_exit',true);
  }
  if(skipMedia){await busTest();return;}

  // Actual LiveKit host + two independent participant contexts, including late join.
  fixture('place',{city,users:users.map(u=>u.id)});await wait(1000);
  const event=await a.api('/events',{title:'Local QA event '+city,description:'Automated local acceptance only',city,starts_at:Date.now()/1000,communication_mode:'liveface',venue_experience_type:'auditorium',venue_mode:'grand_arena',event_type:'Public Talk'});
  await reserveArena(a,event);const started=await a.api('/events/'+event.id+'/state/start',{});console.log('Event started',event.id);await b.api('/events/'+event.id+'/join',{});await b.api('/events/'+event.id+'/venue/enter',{});
  // Venue state arrives separately from media state. Wait out the loading overlay
  // before joining, so accessible controls are inspected in the settled event scene.
  for(const u of [a,b])await u.page.locator('.in-auditorium .world-canvas[data-ready=true]').waitFor({timeout:60000});
  await controls(a,/Reconnect|Join LiveFace/);await until(()=>a.page.locator('.live-dock.is-connected').count(),'Host joined with devices off');check('event_devices_off_on_join',await a.page.getByRole('button',{name:'Camera On',exact:true}).count()===1&&await a.page.getByRole('button',{name:'Unmute',exact:true}).count()===1);await controls(a,/Camera On/);await controls(a,/Unmute/);await Promise.all([video(b,a.id),audio(b,a.id)]);
  const c=await user(city,2);users.push(c);await c.api('/events/'+event.id+'/join',{});await c.api('/events/'+event.id+'/venue/enter',{});
  await Promise.all([video(c,a.id),audio(c,a.id)]);check('event_speaker_two_receivers',true);check('event_late_join',true);for(const control of [/Expand/,/Full Screen/,/Exit Full Screen/,/Minimise/]){await controls(c,control);await audio(c,a.id)}check('event_touch_layout_continuity',true);
  await controls(a,/Camera Off/);await wait(800);await Promise.all([audio(b,a.id),audio(c,a.id)]);check('event_camera_off_audio_continues',true);
  await controls(a,/Camera On/);await Promise.all([video(b,a.id),video(c,a.id)]);check('event_camera_returns',true);
  await controls(a,/^Mute$/);await until(()=>b.page.locator('.remote-tile[data-peer-id="'+a.id+'"] audio').evaluateAll(es=>es.length===0||es.every(e=>e.muted)),'Muted speaker');
  await controls(a,/Unmute/);await Promise.all([audio(b,a.id),audio(c,a.id)]);check('event_mute_unmute',true);
  // Host + three receivers. Browser-selected synthetic desktop capture, real WebRTC.
  const eventPositions=await settled([a,b,c]);
  await a.page.getByLabel('Screen audio options',{exact:true}).click();await a.page.locator('.event-share-controls input[type=checkbox]').check();await a.page.getByLabel('Screen audio options',{exact:true}).click();
  await a.page.locator('.event-share-controls').getByRole('button',{name:'Share screen',exact:true}).click();
  const screenState=await until(async()=>{const d=await a.api('/events/'+event.id);return d.presentation.presenter_id===a.id&&d.presentation.screen_track_id?d.presentation:null},'Host screen publication');
  const screenVideo=async u=>until(()=>u.page.locator('.presentation-sources video[data-track-source="screen_share"]').evaluateAll(es=>es.some(e=>e.videoWidth>0&&e.readyState>=2)),'Decoded shared screen');
  await Promise.all([screenVideo(b),screenVideo(c),video(b,a.id),audio(b,a.id)]);
  check('screen_and_webcam_separate',await b.page.locator('.remote-tile[data-peer-id="'+a.id+'"] video[data-track-source="camera"]').count()===1);
  check('screen_share_keeps_mic',true);
  const d=await user(city,3);users.push(d);await d.api('/events/'+event.id+'/join',{});await d.api('/events/'+event.id+'/venue/enter',{});
  await Promise.all([screenVideo(d),video(d,a.id),audio(d,a.id)]);check('screen_share_three_receivers_and_late_join',true);
  if(screenState.screen_audio_track_id){await until(()=>b.page.locator('.presentation-sources audio').evaluateAll(es=>es.some(e=>e.srcObject&&!e.muted)),'Shared audio source attached');check('screen_audio_source_separate',true)}
  check('presentation_starts_collapsed',await b.page.locator('.presentation-view').isHidden());for(const u of [a,b,c,d])await controls(u,/View stage/);await a.page.locator('.presentation-view').getByRole('button',{name:'Full screen',exact:true}).click();
  check('host_fullscreen_local_only',await a.page.locator('.presentation-fullscreen').count()===1&&await b.page.locator('.presentation-normal').count()===1&&await c.page.locator('.presentation-normal').count()===1);
  await audio(b,a.id);await a.page.locator('.presentation-view').getByRole('button',{name:'Exit full screen',exact:true}).click();
  await b.page.locator('.presentation-view').getByRole('button',{name:'Expand',exact:true}).click();
  check('participant_expand_local_only',await b.page.locator('.presentation-expanded').count()===1&&await d.page.locator('.presentation-normal').count()===1);
  await b.page.locator('.presentation-view').getByRole('button',{name:'Normal view',exact:true}).click();
  await b.page.locator('.presentation-view').getByRole('button',{name:'Full screen',exact:true}).click();
  await c.page.locator('.presentation-view').getByRole('button',{name:'Minimise presentation',exact:true}).click();
  check('presentation_local_views_independent',await b.page.locator('.presentation-fullscreen').count()===1&&await c.page.locator('.presentation-mini').count()===1&&await d.page.locator('.presentation-normal').count()===1);
  await audio(b,a.id);await audio(c,a.id);await screenVideo(d);
  check('presentation_no_position_reset',[a,b,c].every((u,i)=>JSON.stringify(position(u))===JSON.stringify(eventPositions[i])));
  const layout=(await a.api('/events/'+event.id)).presentation;
  check('local_view_not_in_shared_state',layout.screen_track_id===screenState.screen_track_id&&!('fullscreen' in layout)&&!('expanded' in layout));
  await b.page.locator('.presentation-view').getByRole('button',{name:'Exit full screen',exact:true}).click();
  await b.page.locator('.presentation-view').getByRole('button',{name:'Back to Event',exact:true}).click();
  check('presentation_back_to_event',await b.page.locator('.presentation-view').isHidden()&&await b.page.locator('.live-dock.is-connected').count()===1);await audio(b,a.id);
  await controls(b,/View stage/);
  await b.page.locator('.event-share-controls').getByRole('button',{name:'Request to share screen',exact:true}).click();
  const requested=await until(async()=>{const e=await a.api('/events/'+event.id);return e.participants.find(p=>p.id===b.id)?.share_state==='pending'},'Separate share request');
  check('screen_request_separate_from_hand',requested&&(await a.api('/events/'+event.id)).participants.find(p=>p.id===b.id).hand===false);
  await a.api('/events/'+event.id+'/presentation/people/'+b.id+'/allow',{});
  await a.api('/events/'+event.id+'/presentation/people/'+b.id+'/switch',{});
  await until(()=>b.page.locator('.event-share-controls').getByRole('button',{name:'Share screen',exact:true}).count(),'Approved share controls');
  await b.page.locator('.event-share-controls').getByRole('button',{name:'Share screen',exact:true}).click();
  await until(async()=> (await a.api('/events/'+event.id)).presentation.presenter_id===b.id,'Presenter switch B');
  await Promise.all([screenVideo(a),screenVideo(c),screenVideo(d),audio(c,a.id)]);
  check('audience_screen_without_speaker_permission',(await b.api('/media/'+started.session_id+'/token',{})).can_speak===false);
  check('presenter_switch_without_room_disconnect',await a.page.locator('.live-dock.is-connected').count()===1&&await b.page.locator('.live-dock.is-connected').count()===1);
  await a.api('/events/'+event.id+'/presentation/people/'+b.id+'/revoke',{});
  await until(async()=>(await b.page.locator('.event-share-controls').getByRole('button',{name:'Stop sharing',exact:true}).count())===0,'Revocation stops capture');
  await until(()=>c.page.locator('video[data-stage-selected="true"]').evaluateAll(es=>es.some(e=>e.dataset.trackSource==='camera')),'Speaker camera restored');
  check('revoke_clears_screen_restores_camera',!(await a.api('/events/'+event.id)).presentation.presenter_id);
  await controls(a,/Camera Off/);await until(()=>b.page.locator('.event-wall-poster').isVisible(),'Default stage artwork');await audio(c,a.id);
  check('no_share_no_camera_default_wall',await b.page.locator('.event-wall-poster').textContent().then(v=>v.includes(event.title)));
  await controls(a,/Camera On/);await Promise.all([video(b,a.id),video(c,a.id)]);
  await a.api('/events/'+event.id+'/lighting',{preset:'PURPLE WAVE',intensity:.5,enabled:true,target:'stage'},'PUT');
  await until(()=>[b,c,d].every(u=>u.states.at(-1)?.media.find(s=>s.event_id===event.id)?.presentation?.lighting?.preset==='PURPLE WAVE'),'Shared stage lighting');check('lighting_shared_across_receivers',true);
  await screenshot(b,city+'-presentation');
  // Deliberate stop and a lost presenter both restore the existing speaker wall.
  await a.page.locator('.event-share-controls').getByRole('button',{name:'Share screen',exact:true}).click();
  await until(async()=> (await a.api('/events/'+event.id)).presentation.presenter_id===a.id,'Restart host presentation');await screenVideo(b);
  await a.page.locator('.event-share-controls').getByRole('button',{name:'Stop sharing',exact:true}).click();
  await until(()=>b.page.locator('video[data-stage-selected="true"]').evaluateAll(es=>es.some(e=>e.dataset.trackSource==='camera')),'Stopped screen restores camera');await audio(b,a.id);check('stop_screen_keeps_camera_and_mic',true);
  await a.api('/events/'+event.id+'/presentation/people/'+d.id+'/allow',{});
  await until(()=>d.page.locator('.event-share-controls').getByRole('button',{name:'Share screen',exact:true}).count(),'Late participant approved');
  await d.page.locator('.event-share-controls').getByRole('button',{name:'Share screen',exact:true}).click();
  await until(async()=> (await a.api('/events/'+event.id)).presentation.presenter_id===d.id,'Late participant presenting');await screenVideo(b);
  evidence.disconnectedPresenter={id:d.id,logs:d.logs};await d.context.close();users.pop();
  await until(()=>b.page.locator('video[data-stage-selected="true"]').evaluateAll(es=>es.some(e=>e.dataset.trackSource==='camera')),'Disconnected presenter restores camera',55000);
  await until(async()=>!(await a.api('/events/'+event.id)).presentation.presenter_id,'Disconnected presenter lease cleanup',55000);
  await audio(b,a.id);check('presenter_disconnect_cleanup',true);


  await screenshot(b,city+'-auditorium');await controls(c,/Leave & End/);await until(()=>!c.states.at(-1)?.media.some(s=>s.event_id===event.id&&s.state==='accepted'),'Leave reflected');await c.api('/events/'+event.id+'/join',{});await c.api('/events/'+event.id+'/venue/enter',{});await Promise.all([video(c,a.id),audio(c,a.id)]);check('event_rejoin',true);
  for(const viewport of [{width:390,height:844},{width:820,height:1180}]){await b.page.setViewportSize(viewport);await wait(400);check('layout_'+viewport.width,await b.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await video(b,a.id);await audio(b,a.id);await screenshot(b,city+'-'+viewport.width)}
  await a.api('/events/'+event.id+'/state/end',{});await until(()=>!a.states.at(-1)?.media.some(s=>s.event_id===event.id&&s.state==='accepted'),'Event ended');await b.page.setViewportSize({width:1100,height:760});await busTest();evidence.mediaLogs=users.map(u=>({id:u.id,logs:u.logs}));
 }finally{evidence.mediaLogs=users.map(u=>({id:u.id,logs:u.logs,inputs:u.inputs,lastSnapshots:u.states.slice(-8).map(s=>({at:s.server_time,position:s.position})),lastPosition:position(u),media:u.states.at(-1)?.media.map(s=>({id:s.id,state:s.state,event_id:s.event_id})),stateCount:u.states.length}));for(const [index,u] of users.entries()){fs.writeFileSync(path.join(out,city+'-user-'+index+'.txt'),await u.page.locator('body').innerText({timeout:5000}).catch(()=>'(unresponsive)'));await screenshot(u,city+'-final-'+index).catch(()=>{})}results.push(evidence);fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({results,errors},null,2));await Promise.all(users.map(u=>u.context.close()))}
}
async function eventLayout(){
 const a=await user('london',0);await a.page.locator('.world-canvas[data-ready=true]').waitFor();await screenshot(a,'outside-event');const b=await user('london',1),c=await user('london',2),people=[a,b,c];const checks=[];
 const record=(name,data=true)=>{assert.ok(data,name);checks.push(name);console.log('UI',name,'PASS')};
 const noOverflow=async(page)=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
 try{
  const event=await a.api('/events',{title:'Local QA · Ideas that bring people together',description:'Local responsive fixture',city:'london',starts_at:Date.now()/1000,communication_mode:'text',venue_experience_type:'auditorium',venue_mode:'grand_arena',event_type:'Public Talk'});
  await reserveArena(a,event);await a.api('/events/'+event.id+'/state/start',{});await a.api('/events/'+event.id+'/venue/enter',{});
  for(const u of [b,c]){await u.api('/events/'+event.id+'/join',{});await u.api('/events/'+event.id+'/venue/enter',{});}
  for(const [index,u] of people.entries()){try{await u.page.locator('.in-auditorium .world-canvas[data-ready=true]').waitFor({timeout:60000})}catch(e){fs.writeFileSync(path.join(out,'venue-ready-'+index+'.json'),JSON.stringify({state:u.states.at(-1),body:await u.page.locator('body').innerText(),errors},null,2));await screenshot(u,'venue-ready-'+index);throw e}}
  const viewports=[...([320,360,375,390,393,412,430].map(width=>({width,height:844}))),...([768,820,834,1024].map(width=>({width,height:1180}))),{width:1366,height:768},{width:1440,height:900},{width:1920,height:1080},{width:844,height:390},{width:1180,height:820}];
  for(const v of viewports){
   await b.page.setViewportSize(v);await wait(150);record('participant-'+v.width+'x'+v.height,await noOverflow(b.page));
   record('context-clean-'+v.width+'x'+v.height,await b.page.locator('.drawer:visible,.camera-tools:visible,.city-action-tools:visible,.nearby:visible,.mission:visible').count()===0);
   await b.page.getByRole('button',{name:'Event controls',exact:true}).click();await b.page.locator('.current-event-hub .event-detail').waitFor();
   record('participant-role-'+v.width+'x'+v.height,await b.page.locator('.event-host-tools:visible,.event-discovery:visible').count()===0&&await b.page.getByRole('button',{name:'Enter auditorium',exact:true}).isHidden());
   await b.page.getByRole('button',{name:'Close panel',exact:true}).click();
   if([320,390,820,1440,844].includes(v.width))await screenshot(b,'participant-'+v.width+'x'+v.height);
  }
  for(const width of [320,390,820,1440]){
   await a.page.setViewportSize({width,height:900});await a.page.getByRole('button',{name:'Event controls',exact:true}).click();const host=a.page.locator('.event-host-tools');await host.waitFor();
   for(const tab of ['People','Stage','Lights','Media','Event']){await host.getByRole('button',{name:tab,exact:true}).click();record('host-'+tab+'-'+width,await noOverflow(a.page));if(['People','Lights'].includes(tab))await screenshot(a,'host-'+tab+'-'+width);}
   record('no-tickets-'+width,await host.getByRole('button',{name:'TICKETS',exact:true}).count()===0);
   await host.getByRole('button',{name:'Lights',exact:true}).click();await host.getByRole('button',{name:'PURPLE',exact:true}).click();await until(async()=>(await a.api('/events/'+event.id)).presentation.lighting.preset==='PURPLE WAVE','First tap shared lighting');
   await a.page.getByRole('button',{name:'Close panel',exact:true}).click();await screenshot(a,'host-closed-'+width);
   await a.page.getByRole('button',{name:'Event controls',exact:true}).click();record('tab-retained-'+width,await host.getByRole('button',{name:'Lights',exact:true}).getAttribute('aria-pressed')==='true');await a.page.getByRole('button',{name:'Close panel',exact:true}).click();
  }
  await b.page.setViewportSize({width:390,height:844});await b.page.getByRole('button',{name:/Event chat/}).click();await b.page.getByLabel('Message',{exact:true}).fill('Local UI fixture message');await b.page.getByRole('button',{name:'Send message',exact:true}).click();await b.page.locator('.floating-messages').getByText('Local UI fixture message').waitFor();await screenshot(b,'chat-mobile');record('chat-first-tap',await noOverflow(b.page));await b.page.getByRole('button',{name:'Minimise chat',exact:true}).click();
  await b.page.getByRole('button',{name:'Hide UI',exact:true}).click();record('immersive-restore',await b.page.getByRole('button',{name:'Show controls',exact:true}).isVisible()&&await b.page.getByRole('button',{name:'Leave Event',exact:true}).isVisible());await b.page.getByRole('button',{name:'Show controls',exact:true}).click();
  await b.page.getByRole('button',{name:'Leave Event',exact:true}).click();await until(()=>b.page.locator('.in-auditorium').count().then(n=>n===0),'Exit city UI');await b.page.locator('.world-canvas[data-ready=true]').waitFor({timeout:60000});await b.page.locator('.compact-location').waitFor({timeout:60000});record('city-navigation-restored',await b.page.locator('.compact-location').isVisible()&&await b.page.locator('.bottom-nav').isVisible());
  await b.page.evaluate(()=>window.dispatchEvent(new CustomEvent('pulse-open-event',{detail:''})));await b.page.getByRole('button',{name:'＋ Create Event',exact:true}).waitFor();record('event-browser-restored',await b.page.locator('.event-discovery').isVisible());await b.page.getByRole('button',{name:'Close panel',exact:true}).click();
  const cities=await b.api('/cities');record('active-country-metadata',cities.filter(c=>c.enabled&&c.public!==false&&c.joinable!==false).every(c=>/^[A-Z]{2}$/.test(c.country)));
  await b.page.setViewportSize({width:1440,height:900});await b.page.getByRole('button',{name:/Cities & virtual passport/}).click();await b.page.locator('.destination-card').first().waitFor();await screenshot(b,'world-selector-flags');record('flags-visible',await b.page.locator('.destination-name img.country-flag').evaluateAll(flags=>flags.length>0&&flags.every(f=>f.complete&&f.naturalWidth>0)));
  record('no-browser-errors',errors.length===0);fs.writeFileSync(path.join(out,'ui-results.json'),JSON.stringify({checks,viewports,errors},null,2));
 }finally{await Promise.all(people.map(u=>u.context.close()))}
}
async function stableProjectedTile(tile,id){
 let previous,stableSince=Date.now();
 return until(async()=>{
  const value=await tile.evaluate((el,id)=>{const a=window.__qaAnchors[id],r=el.getBoundingClientRect();return a?.visible&&el.classList.contains('avatar-anchored')&&Math.abs(r.x+r.width/2-a.x)<2&&r.width<=128&&r.height<=82?{x:r.x,y:r.y,width:r.width,height:r.height,anchor:a}:null},id);
  if(!value||!previous||Math.hypot(value.x-previous.x,value.y-previous.y)>.5)stableSince=Date.now();previous=value;
  return value&&Date.now()-stableSince>500?value:null;
 },'Stable projected camera tile');
}
async function moveDistance(u,x,z,distance){
 // Stop in the input-owning browser on the actual acknowledgement. A 500 ms
 // observer snapshot or a busy CDP round trip must not keep a fast avatar running.
 await u.page.evaluate(({x,z,distance})=>new Promise((resolve,reject)=>{
  const start=window.__qaMotion;if(!start)return reject(Error('No acknowledged position'));
  const stop=error=>{clearTimeout(timer);window.removeEventListener('qa-motion',observe);window.dispatchEvent(new CustomEvent('pulse-drive-input',{detail:[0,0]}));error?reject(error):resolve()};
  const observe=e=>{const p=e.detail;if(Math.hypot(p.x-start.x,p.z-start.z)>=distance)stop()};
  const timer=setTimeout(()=>stop(Error('Acknowledged movement timed out')),15000);window.addEventListener('qa-motion',observe);window.dispatchEvent(new CustomEvent('pulse-drive-input',{detail:[x,z]}));
 }),{x,z,distance});
}
async function eventMediaLayout(){
 const a=await user('london',0),b=await user('london',1),c=await user('london',2),users=[a,b,c],checks=[];const check=(name,v=true)=>{assert.ok(v,name);checks.push(name);console.log('MEDIA UI',name,'PASS')};
 try{
  const event=await a.api('/events',{title:'Local QA · Live stage presentation',description:'Local synthetic-media visual acceptance',city:'london',starts_at:Date.now()/1000,communication_mode:'liveface',venue_experience_type:'auditorium',venue_mode:'grand_arena',event_type:'Public Talk'});
  await reserveArena(a,event);await a.api('/events/'+event.id+'/state/start',{});await a.api('/events/'+event.id+'/venue/enter',{});for(const u of [b,c]){await u.api('/events/'+event.id+'/join',{});await u.api('/events/'+event.id+'/venue/enter',{})}await b.page.bringToFront();
  for(const [index,u] of users.entries()){try{await u.page.locator('.in-auditorium .world-canvas[data-ready=true]').waitFor({timeout:60000})}catch(e){fs.writeFileSync(path.join(out,'venue-ready-'+index+'.json'),JSON.stringify({state:u.states.at(-1),body:await u.page.locator('body').innerText(),errors},null,2));throw e}}await controls(a,/Reconnect|Join LiveFace/);await until(()=>a.page.locator('.live-dock.is-connected').count(),'Host joined with devices off');check('event_devices_off_on_join',await a.page.getByRole('button',{name:'Camera On',exact:true}).count()===1&&await a.page.getByRole('button',{name:'Unmute',exact:true}).count()===1);await controls(a,/Camera On/);await controls(a,/Unmute/);await b.page.bringToFront();const retried=new Set();await until(async()=>{for(const u of users){if(await u.page.locator('.live-dock.is-connected').count())continue;if(!retried.has(u.id)&&u.logs.some(line=>line.includes('join_failed'))){retried.add(u.id);console.log('MEDIA UI retry observed local transport failure',u.id);await controls(u,/Reconnect|Join LiveFace/)}}return(await Promise.all(users.map(u=>u.page.locator('.live-dock.is-connected').count()))).every(n=>n===1)},'Three fully connected media sessions',90000);await Promise.all([video(b,a.id),audio(b,a.id),video(c,a.id),audio(c,a.id)]);check('three-user-media');
  const tile=b.page.locator('.remote-tile[data-peer-id="'+a.id+'"]');await tile.locator('video').waitFor();await until(()=>tile.evaluate(el=>el.classList.contains('avatar-anchored')),'Actual projected camera tile');
  const before=await stableProjectedTile(tile,a.id),anchor=before.anchor;check('head-projection',Math.abs(before.x+before.width/2-anchor.x)<12&&before.width<=128&&before.height<=82);await screenshot(b,'avatar-video-desktop');
  await moveDistance(a,.6,0,.75);await until(async()=>Math.abs((await tile.boundingBox()).x-before.x)>3,'Tile follows moving host');await video(b,a.id);check('video-follows-avatar');await screenshot(b,'avatar-video-moved');
  // Moving the observer must keep the remote identity attached without a reconnect
  // or a scene/position reset. The server's role promotion relocation is tested later.
  const observerStart=position(b),hostStable=position(a),disconnects=b.logs.filter(s=>s.includes('room_disconnect')).length;
  await moveDistance(b,.35,0,.5);await settled([a,b]);const observerEnd=position(b);
  check('participant-movement',observerEnd.zone===observerStart.zone&&Math.hypot(observerEnd.x-observerStart.x,observerEnd.z-observerStart.z)>.05&&Math.hypot(observerEnd.x-observerStart.x,observerEnd.z-observerStart.z)<8);
  check('movement-keeps-location',position(a).zone===hostStable.zone&&Math.hypot(position(a).x-hostStable.x,position(a).z-hostStable.z)<.1);
  await until(async()=>tile.evaluate((el,id)=>{const a=window.__qaAnchors[id],r=el.getBoundingClientRect();return a?.visible&&el.dataset.peerId===id&&Math.abs(r.x+r.width/2-a.x)<12},a.id),'Observer movement keeps host anchor');await video(b,a.id);await audio(b,a.id);check('participant-movement-keeps-media',b.logs.filter(s=>s.includes('room_disconnect')).length===disconnects);
  const canvas=await b.page.locator('.world-canvas canvas').elementHandle();await b.page.getByRole('button',{name:'Event controls',exact:true}).click();await b.page.getByRole('button',{name:'Close panel',exact:true}).click();check('drawer-keeps-canvas',await b.page.evaluate(el=>el===document.querySelector('.world-canvas canvas'),canvas));await audio(b,a.id);check('drawer-keeps-media');
  await a.api('/events/'+event.id+'/people/'+b.id+'/cohost',{});await b.page.getByRole('button',{name:'Event controls',exact:true}).click();const host=b.page.locator('.event-host-tools');await host.waitFor();for(const tab of ['People','Lights']){await host.getByRole('button',{name:tab,exact:true}).click();await screenshot(b,'host-3d-'+tab)}await b.page.getByRole('button',{name:'Close panel',exact:true}).click();
  await a.api('/events/'+event.id+'/people/'+c.id+'/speaker',{});await until(async()=>!(await c.page.getByRole('button',{name:'Camera On',exact:true}).isDisabled()),'Speaker camera permission');await controls(c,'Camera On');await video(b,c.id);
  const speakerTile=b.page.locator('.remote-tile[data-peer-id="'+c.id+'"]');await settled([a,b,c]);
  // Decoded video does not guarantee that a newly promoted speaker has been
  // projected. Establish an anchored baseline, then wait for the rendered move.
  const speakerBefore=await stableProjectedTile(speakerTile,c.id),speakerStart=position(c);const mediaBefore=b.logs.filter(s=>s.includes('room_disconnect')).length;
  await moveDistance(c,.4,0,.5);await settled([a,b,c]);const speakerEnd=position(c);
  check('speaker-movement-no-teleport',speakerEnd.zone===speakerStart.zone&&Math.hypot(speakerEnd.x-speakerStart.x,speakerEnd.z-speakerStart.z)>.05&&Math.hypot(speakerEnd.x-speakerStart.x,speakerEnd.z-speakerStart.z)<8);
  await until(async()=>speakerTile.evaluate((el,{id,startX})=>{const a=window.__qaAnchors[id],r=el.getBoundingClientRect();return a?.visible&&el.classList.contains('avatar-anchored')&&Math.abs(r.x+r.width/2-a.x)<12&&Math.abs(r.x-startX)>2},{id:c.id,startX:speakerBefore.x}),'Moving speaker tile follows correct avatar');const speakerAfter=await speakerTile.boundingBox();fs.writeFileSync(path.join(out,'speaker-movement.json'),JSON.stringify({speakerStart,speakerEnd,speakerBefore,speakerAfter},null,2));check('speaker-tile-moves',Math.abs(speakerAfter.x-speakerBefore.x)>2);await Promise.all([video(b,a.id),video(b,c.id)]);check('two-camera-identities-preserved',await b.page.locator('.remote-tile[data-peer-id="'+a.id+'"]').count()===1&&await speakerTile.count()===1&&b.logs.filter(s=>s.includes('room_disconnect')).length===mediaBefore);await screenshot(b,'two-speakers-moved');
  // Bring both speakers into the mobile field of view through ordinary movement.
  // A camera card for an off-screen avatar is correctly hidden, not a mobile pass.
  for(const speaker of [a,c]){const x=position(speaker).x;if(Math.abs(x)>1.5)await moveDistance(speaker,-Math.sign(x)*.18,0,Math.abs(x)-.5)}
  await a.api('/events/'+event.id+'/people/'+b.id+'/audience',{});await until(()=>b.states.at(-1)?.media.find(s=>s.event_id===event.id)?.event_role==='audience','Return observer to audience after host-role checks');await settled([a,b,c]);await b.page.setViewportSize({width:390,height:844});await until(()=>b.page.evaluate(ids=>window.__qaAnchorViewport?.width===390&&ids.every(id=>window.__qaAnchors[id]?.visible),[a.id,c.id]),'Both avatars projected in resized mobile scene');await until(async()=>{const box=await tile.boundingBox();return await tile.isVisible()&&await speakerTile.isVisible()&&!!box&&box.width<=96},'Visible mobile avatar camera');check('mobile-video-size',(await tile.boundingBox()).width<=96);await until(async()=>{const first=await tile.boundingBox(),second=await speakerTile.boundingBox();return first&&second&&(first.x+first.width<=second.x||second.x+second.width<=first.x||first.y+first.height<=second.y||second.y+second.height<=first.y)},'Separate mobile speaker cards');check('mobile-camera-cards-do-not-overlap');await screenshot(b,'avatar-video-mobile');await b.page.setViewportSize({width:820,height:1180});await until(()=>b.page.evaluate(()=>window.__qaAnchorViewport?.width===820),'Tablet projection resized');await screenshot(b,'avatar-video-tablet');await b.page.setViewportSize({width:1440,height:900});await until(()=>b.page.evaluate(()=>window.__qaAnchorViewport?.width===1440),'Desktop projection resized');
  await a.page.getByRole('button',{name:'Share screen',exact:true}).click();await until(()=>b.page.locator('.presentation-sources video[data-track-source="screen_share"]').evaluateAll(es=>es.some(e=>e.videoWidth>0&&e.readyState>=2)),'Screen decoded on wall');check('wall-share-with-mini-camera',await b.page.locator('.presentation-view').isHidden()&&await tile.locator('video').count()===1);await screenshot(b,'screen-share-active');await audio(b,a.id);await a.page.getByRole('button',{name:'Stop sharing',exact:true}).click();check('share-stops-without-call-loss',await b.page.locator('.live-dock.is-connected').count()===1);
  const retainedCanvas=await b.page.locator('.world-canvas canvas').elementHandle(),transitionStarted=Date.now();
  await controls(b,/Leave & End/);await until(()=>!b.states.at(-1)?.media.some(s=>s.event_id===event.id&&s.state==='accepted'),'Observer leaves media');await until(()=>b.page.locator('.in-auditorium').count().then(n=>n===0),'Observer returns to city');await b.page.locator('.world-canvas[data-ready=true]').waitFor({timeout:60000});check('city-return-reuses-gpu-context',await b.page.evaluate(canvas=>canvas===document.querySelector('.world-canvas canvas'),retainedCanvas));console.log('City return milliseconds',Date.now()-transitionStarted);await b.api('/events/'+event.id+'/join',{});await b.api('/events/'+event.id+'/venue/enter',{});await b.page.locator('.in-auditorium .world-canvas[data-ready=true]').waitFor({timeout:60000});check('venue-reentry-reuses-gpu-context',await b.page.evaluate(canvas=>canvas===document.querySelector('.world-canvas canvas'),retainedCanvas));await b.page.locator('.live-dock.is-connected').waitFor({timeout:60000});await video(b,a.id);await audio(b,a.id);check('observer-rejoins-real-3d-media');
  check('no-browser-errors',errors.length===0);fs.writeFileSync(path.join(out,'event-media-ui.json'),JSON.stringify({checks,errors},null,2));
 }finally{for(const [i,u] of users.entries()){fs.writeFileSync(path.join(out,'media-final-'+i+'.json'),JSON.stringify({render:await u.page.evaluate(()=>({at:performance.now(),gpu:window.__qaGpu,events:window.__qaRenderEvents,ready:document.querySelector('.world-canvas')?.dataset.ready,canvas:[...document.querySelectorAll('.world-canvas canvas')].map(c=>({width:c.width,height:c.height,cssWidth:c.clientWidth,cssHeight:c.clientHeight}))})),rtc:await u.page.evaluate(()=>window.__qaRtc),visibility:await u.page.evaluate(()=>document.visibilityState),body:await u.page.locator('body').innerText().catch(()=>''),logs:u.logs,errors,state:u.states.at(-1)},null,2));await screenshot(u,'media-final-'+i).catch(()=>{});await u.context.close()}}
}
async function worldPolish(){
 const checks=[],measurements=[];const record=(name,value)=>{assert.ok(value,name);checks.push(name);console.log('UI',name,'PASS')};
 const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage();
 let release;const gate=new Promise(r=>release=r);let requests=0;
 await page.route('**/api/geography/milton-keynes',async route=>{requests++;await gate;await route.continue()});
 await page.goto(origin);await page.locator('.auth-card').waitFor();await page.getByLabel('Email or username',{exact:true}).fill('readiness check');await screenshot({page},'authentication-ready');record('authentication-independent-of-geography',await page.locator('.world-canvas canvas').count()===0);release();
 const refresh=Date.now();await page.reload();await page.locator('.auth-card').waitFor({timeout:60000});measurements.push({name:'authentication-refresh',ms:Date.now()-refresh});record('refresh-authentication-ready',await page.getByRole('button',{name:'Enter Mindaam',exact:true}).isVisible());await context.close();
 // Real local signup/login/onboarding flow; no production account or seed data.
 const signup=await browser.newContext({viewport:{width:390,height:844}});await signup.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){return kind==='webgl'||kind==='webgl2'?null:get.call(this,kind,...args)}});const signupPage=await signup.newPage();signupPage.on('pageerror',e=>errors.push({flow:'signup',error:e.message}));
 try{
  const name='qaflags'+Date.now().toString(36),headers={Origin:origin,'X-Pulse-Client':'web'},password='LocalBrowserQA2026!pass';
  const registered=await signup.request.post(origin+'/api/auth/register',{headers,data:{email:name+'@example.test',username:name,password,confirm_password:password,adult:true,accepted_terms:true,accepted_privacy:true}});assert.equal(registered.status(),201);await signup.request.post(origin+'/api/auth/logout',{headers,data:{}});
  await signupPage.goto(origin);await signupPage.getByLabel('Email or username',{exact:true}).fill(name);await signupPage.getByLabel('Password',{exact:true}).fill(password);await signupPage.getByRole('button',{name:'Enter Mindaam',exact:true}).click();await signupPage.locator('.onboarding').waitFor();record('new-user-browser-login',true);
  const destination=signupPage.locator('.starter-picker select');record('signup-native-country-codes',await destination.locator('option').evaluateAll(es=>es.filter(e=>e.value).every(e=>/^[A-Z]{2} /.test(e.textContent))));
  for(const [index,width] of [320,360,375,390,393,412,430,768,820,834,1024,1366,1440,1920].entries()){
   await signupPage.setViewportSize({width,height:900});await destination.selectOption(index%2?'sydney':'london');await until(()=>signupPage.locator('.starter-preview img.country-flag').evaluateAll(es=>es.length===1&&es[0].complete&&es[0].naturalWidth>0),'Signup SVG flag');record('signup-flags-'+width,await signupPage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  }
  await destination.selectOption('london');await signupPage.locator('.starter-preview input[type=checkbox]').check();await signupPage.getByRole('button',{name:'Let’s explore',exact:true}).click();await signupPage.locator('.welcome-home .destination-card.is-owned').first().waitFor();record('new-user-welcome',true);await signupPage.reload();await signupPage.locator('.welcome-home .destination-card.is-owned').first().waitFor();record('returning-user-refresh',true);
  await signupPage.goto(origin+'/explore');await signupPage.locator('#preview-city option[value=sydney]').waitFor({state:'attached'});record('explorer-native-country-codes',await signupPage.locator('#preview-city option').evaluateAll(es=>es.length>0&&es.every(e=>/^(✓ )?[A-Z]{2} /.test(e.textContent))));
 }finally{await signup.close()}
 for(const city of ['london','sydney']){
  const u=await user(city,0);try{
   await u.page.locator('.world-canvas[data-ready=true]').waitFor();
   const cities=await u.api('/cities');for(const code of new Set(cities.filter(c=>c.enabled&&c.public!==false&&c.joinable!==false).map(c=>c.country))){const asset=await u.context.request.get(origin+'/flags/'+code.toLowerCase()+'.svg');record(city+'-active-flag-'+code,asset.ok()&&(await asset.text()).includes('<svg'));}
   await u.page.getByRole('button',{name:'Open district map',exact:true}).click();const markers=u.page.locator('.world-minimap.expanded .map-business');await markers.first().waitFor();const names=await markers.evaluateAll(es=>es.slice(0,2).map(e=>e.getAttribute('aria-label'))),businesses=[];record(city+'-existing-businesses',names.length===2);
   for(const [index,name] of names.entries()){
    await u.page.setViewportSize(index?{width:390,height:844}:{width:1440,height:900});const [response]=await Promise.all([u.page.waitForResponse(r=>r.url().includes('/api/business-pois/')),markers.filter({has:u.page.locator('title',{hasText:name.slice(5)})}).first().locator('circle').click()]);assert.ok(response.ok());const data=await response.json();businesses.push(data);const card=u.page.locator('.business-card-popup');await card.waitFor();
    record(city+'-business-'+index,await card.getByRole('heading',{name:data.name,exact:true}).count()===1&&await card.locator('.business-category').textContent()===data.category.replaceAll('_',' '));
    record(city+'-conditional-fields-'+index,await card.locator('.business-description').count()===(data.description?1:0)&&await card.getByRole('link',{name:/Visit website/}).count()===(data.website?1:0));
    record(city+'-directions-'+index,await card.getByRole('link',{name:/Get directions/}).getAttribute('href')===data.directions_url);record(city+'-ask-coming-soon-'+index,await card.getByRole('button',{name:/Ask Me.*Coming soon/}).count()===1);
    record(city+'-card-bounds-'+index,await card.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth&&b.top>=0&&b.bottom<=innerHeight&&el.scrollWidth<=el.clientWidth}));await screenshot(u,city+'-business-'+index);await card.getByRole('button',{name:'Close business',exact:true}).click();record(city+'-close-'+index,await card.count()===0);
   }
   // Delay a real first response while selecting a second existing business.
   let releaseBusiness,firstRequested;const businessGate=new Promise(r=>releaseBusiness=r),businessStarted=new Promise(r=>firstRequested=r);let delayed=false;
   await u.page.route('**/api/business-cards/*',async route=>{if(!delayed){delayed=true;const response=await route.fetch();firstRequested();await businessGate;await route.fulfill({response})}else await route.continue()});
   await u.page.evaluate(b=>window.dispatchEvent(new CustomEvent('pulse-business-card',{detail:b})),{id:businesses[0].id});await businessStarted;await u.page.evaluate(b=>window.dispatchEvent(new CustomEvent('pulse-business-card',{detail:b})),{id:businesses[1].id});await u.page.locator('.business-card-popup').getByRole('heading',{name:businesses[1].name,exact:true}).waitFor();releaseBusiness();await wait(400);record(city+'-stale-response-discarded',await u.page.locator('.business-card-popup').getByRole('heading',{name:businesses[1].name,exact:true}).count()===1);await u.page.unroute('**/api/business-cards/*');await u.page.getByRole('button',{name:'Close business',exact:true}).click();
   // Exercise the existing WelcomeHome parser against both documented payload shapes.
   for(const [name,body,count] of [['array-empty',[],0],['object-empty',{missions:[]},0],['object-available',{missions:[{id:'local-presentation-fixture',completed:false}]},1]]){
    await u.page.route('**/api/missions',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)}));await u.page.reload();await u.page.locator('.welcome-home').waitFor();await u.page.locator('.destination-card.is-owned').first().waitFor();await until(()=>u.page.locator('.welcome-home').getByText(count+' available missions',{exact:true}).count(),'Welcome mission contract '+name);record(city+'-welcome-'+name,true);await u.page.unroute('**/api/missions');
   }
   for(const width of [320,360,375,390,393,412,430,768,820,834,1024,1366,1440,1920]){
    await u.page.setViewportSize({width,height:900});await until(()=>u.page.locator('.destination-name img.country-flag').evaluateAll(es=>es.length>0&&es.every(e=>e.complete&&e.naturalWidth>0)),'Flags at '+width);record(city+'-welcome-flags-'+width,await u.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   }
  }finally{await u.context.close()}
 }
 fs.writeFileSync(path.join(out,'world-polish.json'),JSON.stringify({checks,measurements,errors},null,2));record('no-browser-errors',errors.length===0);
}
async function main(){
 fixture('init');
 if(!skipMedia)start(process.env.QA_LIVEKIT||'/tmp/mylil-livekit-server',['--config-body','rtc:\n  enable_loopback_candidate: true\n','--dev','--bind','127.0.0.1','--node-ip','127.0.0.1','--keys',env.LIVEKIT_API_KEY+': '+env.LIVEKIT_API_SECRET],'livekit.log');
 start(python,['-m','uvicorn','backend.api.main:app','--host','127.0.0.1','--port','8000'],'api.log');
 start(process.execPath,['node_modules/next/dist/bin/next','start','apps/consumer-web','--hostname','127.0.0.1','--port','3000'],'web.log');
 await Promise.all([ready(origin),ready('http://127.0.0.1:8000/api/health'),...(skipMedia?[]:[ready('http://127.0.0.1:7880')])]);
 browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM||'/tmp/mylil-chromium/chromium',headless:true,args:[...(mapRenderer?['--disable-webgl']:[]),'--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--auto-select-desktop-capture-source=Entire screen','--use-file-for-fake-audio-capture=/tmp/mylil-test-tone.wav','--disable-background-timer-throttling']});
 if(process.env.QA_EVENT_MEDIA_UI==='1'){await eventMediaLayout();return}
 if(process.env.QA_WORLD_POLISH==='1'){await worldPolish();return}
 if(process.env.QA_EVENT_LAYOUT==='1'){await eventLayout();return}
 for(const city of (process.env.QA_CITIES||'london,birmingham,madrid,dubai,mumbai,new-york,sydney').split(','))await runCity(city);
 assert.equal(errors.length,0,JSON.stringify(errors));console.log('Acceptance completed',results.map(r=>({city:r.city,checks:Object.keys(r.checks).length})));
}
main().catch(e=>{console.error(e);fs.writeFileSync(path.join(out,'failure.txt'),e.stack);process.exitCode=1}).finally(async()=>{
 await browser?.close();
 // Each CI step owns these children. Wait for shutdown before the next step
 // can connect to the same ports with a different isolated fixture database.
 await Promise.all(children.map(p=>new Promise(resolve=>{
  if(p.exitCode!==null||p.signalCode!==null)return resolve();
  const timer=setTimeout(()=>p.kill('SIGKILL'),5000);
  p.once('exit',()=>{clearTimeout(timer);resolve()});p.kill('SIGTERM');
 })));
});
