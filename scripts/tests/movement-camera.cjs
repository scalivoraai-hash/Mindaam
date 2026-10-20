/* Runs against a disposable local API and production Next build, never production data. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),{execFileSync,spawn}=require('child_process');
const {chromium}=require((process.env.QA_NODE_MODULES||'/tmp/mylil-motion-tools/node_modules')+'/playwright');
const root=path.resolve(__dirname,'../..'),origin='http://127.0.0.1:3000',python=process.env.QA_PYTHON||'/tmp/mylil-motion-qa/bin/python';
const out=process.env.QA_OUTPUT||'/tmp/mylil-motion-evidence';fs.mkdirSync(out,{recursive:true});
const env={...process.env,APP_ENV:'local',DATABASE_URL:process.env.DATABASE_URL||('sqlite:////tmp/mylil-multi-motion-'+Date.now()+'.db')};
const baseline=process.env.QA_BASELINE==='1',wait=ms=>new Promise(r=>setTimeout(r,ms)),results={baseline,speeds:[],checks:[]};
const fixture=data=>JSON.parse(execFileSync(python,['-m','scripts.tests.motion_fixture',JSON.stringify(data)],{cwd:root,env,encoding:'utf8'}));
async function until(fn,label,timeout=60000){const end=Date.now()+timeout;while(Date.now()<end){if(await fn())return;await wait(100)}throw Error('Timed out: '+label)}
function check(name,value){assert.ok(value,name);results.checks.push(name);console.log(name,'PASS')}
async function main(){
 execFileSync(python,['-m','scripts.tests.multiplayer_fixture','init'],{cwd:root,env,stdio:'pipe'});
 const children=[];for(const [bin,args,log] of [[python,['-m','uvicorn','backend.api.main:app','--host','127.0.0.1','--port','8000'],'api'],[process.execPath,['node_modules/next/dist/bin/next','start','apps/consumer-web','--hostname','127.0.0.1','--port','3000'],'web']]){const fd=fs.openSync(path.join(out,log+'.log'),'w');children.push(spawn(bin,args,{cwd:log==='api'?(process.env.QA_API_ROOT||root):root,env:{...env,PUBLIC_ORIGIN:origin},stdio:['ignore',fd,fd]}))}
 await until(async()=>{try{return (await fetch(origin+'/api/health')).ok}catch{return false}},'application startup');
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM||'/tmp/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-webgl','--disable-background-timer-throttling']});
 try{
 const city=process.env.QA_CITY||'milton-keynes',route=fixture({city}),context=await browser.newContext(),page=await context.newPage();
 await page.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){return /webgl/.test(kind)?null:get.call(this,kind,...args)}});
 const api=async(url,data)=>{const r=await context.request.fetch(origin+'/api'+url,{method:data===undefined?'GET':'POST',data,headers:{Origin:origin,'X-Pulse-Client':'web'}});assert.ok(r.ok(),url+' '+await r.text());return r.json()};
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const frames=[],sent=new Map();page.on('websocket',ws=>{ws.on('framesent',f=>{try{const d=JSON.parse(f.payload.toString());if(d.type==='input')sent.set(d.seq,Date.now())}catch{}});ws.on('framereceived',f=>{try{const d=JSON.parse(f.payload.toString());if(d.type==='motion'||d.type==='state')frames.push({at:Date.now(),roundTripMs:d.type==='motion'&&sent.has(d.seq)?Date.now()-sent.get(d.seq):undefined,...d})}catch{}})});
 const input=(x,z)=>page.evaluate(([x,z])=>window.dispatchEvent(new CustomEvent('pulse-drive-input',{detail:[x,z]})),[x,z]);
 const position=()=>page.locator('.world-minimap svg g[transform]').evaluate(el=>el.getAttribute('transform').match(/-?[\d.]+/g).map(Number));
 // Keep the actual preview renderer/input path. Place only the public fixture response on a measured real road.
 await page.route('**/api/world-preview/'+city,async r=>{const response=await r.fetch(),v=await response.json();v.position={...v.position,x:route.x,z:route.z};await r.fulfill({response,json:v})});
 await page.goto(origin+'/explore');if(city!=='milton-keynes')await page.locator('#preview-city').selectOption(city);
 await page.locator('.world-canvas[data-ready=true]').waitFor();
 async function measure(name,direction=route.direction){
   const frameStart=frames.length;
   const {a,b,elapsed}=await page.evaluate(async direction=>{
    const pos=()=>document.querySelector('.world-minimap svg g[transform]').getAttribute('transform').match(/-?[\d.]+/g).map(Number);
    const a=pos(),at=performance.now();window.dispatchEvent(new CustomEvent('pulse-drive-input',{detail:direction}));
    await new Promise(r=>setTimeout(r,3000));window.dispatchEvent(new CustomEvent('pulse-drive-input',{detail:[0,0]}));const elapsed=(performance.now()-at)/1000;
    await new Promise(r=>setTimeout(r,350));return {a,b:pos(),elapsed};
   },direction);
   const measured=frames.slice(frameStart).filter(f=>f.type==='motion'),latencies=measured.map(f=>f.roundTripMs).filter(Number.isFinite).sort((a,b)=>a-b);
   const row={name,distance:Math.hypot(b[0]-a[0],b[1]-a[1]),seconds:elapsed,start:a,end:b};if(latencies.length)row.acknowledgements={count:latencies.length,p50Ms:latencies[Math.floor(latencies.length*.5)],p95Ms:latencies[Math.floor(latencies.length*.95)],maxMs:latencies.at(-1),maxServerGapMs:Math.max(...measured.slice(1).map((f,i)=>(f.position.last_move-measured[i].position.last_move)*1000))};row.mps=row.distance/elapsed;results.speeds.push(row);console.log(JSON.stringify(row));return row;
 }
 const preview=process.env.QA_CAMERA_ONLY?{mps:12.5}:await measure('preview');if(!process.env.QA_CAMERA_ONLY)check('preview moves on measured road',preview.mps>10);
 const name='motion'+Date.now();const user=await api('/auth/register',{email:name+'@example.test',username:name,password:'LocalMotionQA2026!pass',confirm_password:'LocalMotionQA2026!pass',adult:true,accepted_terms:true,accepted_privacy:true});
 await api('/onboarding',{city,interests:[],avatar:{color:'#e58a50'},privacy:'City Mode',location_consent:false,analytics_consent:false});
 await page.goto(origin);await page.locator('.welcome-home').waitFor();await page.locator('.destination-card.is-owned').first().click();await page.locator('.world-access-modal').getByRole('button',{name:/^Enter /}).click();await page.locator('.world-playing').waitFor();await until(()=>frames.some(f=>f.movement_transport),'socket');
 if(process.env.QA_CAMERA_ONLY){await cameraAndPeer(browser,api,user.user.id,city,page,input,frames);await keyboardRegression(page,frames);return}
 async function place(){fixture({city,users:[user.user.id]});await wait(900)}
 await place();await page.getByRole('button',{name:'walk',exact:true}).click();const walk=await measure('authenticated default hold');
 await place();await page.getByRole('button',{name:'run',exact:true}).click();const run=await measure('authenticated explicit run');
 await place();await page.getByRole('button',{name:'walk',exact:true}).click();await measure('authenticated light walk',route.direction.map(n=>n*.6));
 await place();const marker=frames.length;await input(...route.direction);await wait(160);await input(0,0);await wait(300);check('short press remains walk',frames.slice(marker).filter(f=>f.type==='motion').every(f=>f.position.mode==='walk'));
 if(!baseline){
  await place();const marker=frames.length;await input(...route.direction);await wait(1000);await input(0,0);await wait(300);const moving=frames.slice(marker).filter(f=>f.type==='motion'&&f.position.speed>0);console.log('Held input acknowledgements',JSON.stringify(moving.map(f=>({seq:f.seq,mode:f.position.mode,speed:f.position.speed}))));check('held input walks then runs',moving[0].position.mode==='walk'&&moving.some(f=>f.position.mode==='run'));
 }
 // Real rented vehicles, route collision and server time; no constant-only speed assertion.
 const listing=await api('/mobility');await api('/mobility/policy',{version:listing.policy.version,accepted:true});
 for(const kind of ['bike','car']){
  const placed=fixture({city,users:[user.user.id],kind});await wait(800);const assets=await api('/mobility'),asset=assets.assets.find(a=>a.id===placed.asset);
  await api('/mobility/assets/'+placed.asset+'/rent',{id:require('crypto').randomUUID(),expected_cost:asset.cost??asset.price,expected_currency:asset.currency});
  fixture({city,users:[user.user.id],heading:true});await wait(700);await input(0,-1);await wait(baseline?4200:2100);
  // Pair displacement with the timestamps of those same acknowledgements. A short
  // host-clock window can otherwise compare a fresh start to a delayed end frame.
  const first=frames.filter(f=>f.type==='motion'&&f.position.mode===kind).at(-1),at=Date.now();await wait(650);
  const last=frames.filter(f=>f.type==='motion'&&f.position.mode===kind).at(-1);assert.ok(first&&last&&last.position.last_move>first.position.last_move);
  const row={name:kind,distance:Math.hypot(last.position.x-first.position.x,last.position.z-first.position.z),seconds:last.position.last_move-first.position.last_move,browserObservationSeconds:(Date.now()-at)/1000,start:first.position,end:last.position};
  row.mps=row.distance/row.seconds;await input(0,1);await wait(800);await input(0,0);results.speeds.push(row);console.log(JSON.stringify(row));await api('/mobility/exit',{});await wait(800);
 }
 results.frames=frames.filter(f=>f.type==='motion').map(f=>({at:f.at,position:f.position}));
 check('no browser errors',errors.length===0);
 if(!baseline){check('held input reaches running state',results.frames.some(f=>f.position.mode==='run'));check('authenticated held movement exceeds preview pace',walk.mps>=preview.mps*.98);check('run is faster than preview baseline',run.mps>preview.mps*1.3)}
 if(!baseline){
  check('actual bike faster than run',results.speeds.find(s=>s.name==='bike').mps>run.mps);
  check('actual car faster than bike',results.speeds.find(s=>s.name==='car').mps>results.speeds.find(s=>s.name==='bike').mps);
  await cameraAndPeer(browser,api,user.user.id,city,page,input,frames);
  await keyboardRegression(page,frames);
  await pollingRegression(browser,city);
 }
 await page.screenshot({path:path.join(out,'movement.jpg')});
 }finally{fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));await browser.close();for(const c of children)c.kill()}
}
async function keyboardRegression(page,frames){
 // The WebGL observer owns another Chromium process. Close it before checking
 // physical keys in the driver's page so visibility/blur safety is not triggered.
 try{
 await page.bringToFront();await until(()=>page.evaluate(()=>document.visibilityState==='visible'),'keyboard page visible');
 const short=frames.length;await page.keyboard.down('a');await wait(120);await page.keyboard.up('a');await until(()=>frames.slice(short).some(f=>f.type==='motion'&&f.position.speed===0),'short key release acknowledgement');check('keyboard short press walks',frames.slice(short).filter(f=>f.type==='motion').every(f=>f.position.mode==='walk'));
 const held=frames.length;await page.keyboard.down('d');try{await until(()=>frames.slice(held).some(f=>f.type==='motion'&&f.position.mode==='run'&&f.position.speed>0),'held key run acknowledgement')}finally{await page.keyboard.up('d')}await until(()=>frames.slice(held).filter(f=>f.type==='motion').at(-1)?.position.speed===0,'held key release acknowledgement');check('keyboard hold runs and release stops',true);
 }catch(error){fs.writeFileSync(path.join(out,'keyboard-failure.json'),JSON.stringify({page:await page.evaluate(()=>({visibility:document.visibilityState,focus:document.activeElement?.outerHTML,body:document.body.innerText})),frames:frames.slice(-20)},null,2));throw error}
}
async function pollingRegression(browser,city){
 const context=await browser.newContext(),page=await context.newPage();let entryStarted=0,entryCompleted=0,active=0,maximum=0;const polls=[];
 try{
  // No state frames: exercise the genuine HTTP fallback, including a failed sibling
  // read while a world response spans more than two polling ticks.
  await context.routeWebSocket('**/api/realtime',()=>{});
  await page.route('**/api/world/enter',async route=>{entryStarted=Date.now();await wait(4200);const response=await route.fetch();entryCompleted=Date.now();await route.fulfill({response})});
  await page.route('**/api/world/'+city,async route=>{active++;maximum=Math.max(maximum,active);const poll={start:Date.now()};polls.push(poll);try{const response=await route.fetch();await wait(6500);await route.fulfill({response})}finally{poll.end=Date.now();active--}});
  await page.route('**/api/notifications',route=>route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({detail:'Local polling regression fixture'})}));
  const api=async(url,data)=>{const r=await context.request.post(origin+'/api'+url,{data,headers:{Origin:origin,'X-Pulse-Client':'web'}});assert.ok(r.ok(),url);return r.json()};
  const name='polling'+Date.now();await api('/auth/register',{email:name+'@example.test',username:name,password:'LocalMotionQA2026!pass',confirm_password:'LocalMotionQA2026!pass',adult:true,accepted_terms:true,accepted_privacy:true});await api('/onboarding',{city,interests:[],avatar:{color:'#41a8b8'},privacy:'City Mode',location_consent:false,analytics_consent:false});
  await page.goto(origin);await page.locator('.welcome-home').waitFor();await page.locator('.destination-card.is-owned').first().click();await page.locator('.world-access-modal').getByRole('button',{name:/^Enter /}).click();
  await until(()=>entryStarted>0,'delayed entry started');await wait(3600);check('fallback does not poll while entry is pending',entryCompleted===0&&polls.length===0);
  await until(()=>polls.length>=2&&active===0,'two complete delayed fallback batches',40000);
  check('socket grace begins after entry completes',polls[0].start-entryCompleted>=4900);
  check('slow fallback batches never overlap even after a sibling fails',maximum===1&&polls.every((p,i)=>i===0||p.start>=polls[i-1].end));
  results.polling={entryDelayMs:entryCompleted-entryStarted,firstPollAfterEntryMs:polls[0].start-entryCompleted,maxConcurrentWorldRequests:maximum,polls};
 }finally{await context.close()}
}
async function cameraAndPeer(_browser,hostApi,hostId,city,hostPage,input,hostFrames){
 let cameraPage;
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM||'/tmp/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-background-timer-throttling']});
 try{
 const c=await browser.newContext({viewport:{width:1100,height:844},hasTouch:true});
 // Observe the actual rendered view matrix without adding production diagnostics.
 await c.addInitScript(()=>{
  const getContext=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){if(/webgl/.test(kind)&&!document.querySelector('.world-playing'))return null;return getContext.call(this,kind,...args)};
  for(const Type of [WebGLRenderingContext,WebGL2RenderingContext]){
   const names=new WeakMap(),get=Type.prototype.getUniformLocation,set=Type.prototype.uniformMatrix4fv;
   Type.prototype.getUniformLocation=function(program,name){const loc=get.call(this,program,name);if(loc)names.set(loc,name);return loc};
   Type.prototype.uniformMatrix4fv=function(loc,transpose,m,...rest){if(names.get(loc)==='viewMatrix')window.__qaCamera={yaw:Math.atan2(m[2],m[10]),x:-(m[0]*m[12]+m[1]*m[13]+m[2]*m[14]),y:-(m[4]*m[12]+m[5]*m[13]+m[6]*m[14]),z:-(m[8]*m[12]+m[9]*m[13]+m[10]*m[14])};return set.call(this,loc,transpose,m,...rest)};
  }
 });
 const p=await c.newPage(),peerFrames=[],errors=[];cameraPage=p;p.on('pageerror',e=>errors.push(e.message));p.on('websocket',ws=>ws.on('framereceived',f=>{try{const d=JSON.parse(f.payload.toString());if(d.type==='state')peerFrames.push({at:Date.now(),...d})}catch{}}));
 const api=async(url,data)=>{const r=await c.request.fetch(origin+'/api'+url,{method:data===undefined?'GET':'POST',data,headers:{Origin:origin,'X-Pulse-Client':'web'}});assert.ok(r.ok(),url+' '+await r.text());return r.json()};
 const name='observer'+Date.now(),u=await api('/auth/register',{email:name+'@example.test',username:name,password:'LocalMotionQA2026!pass',confirm_password:'LocalMotionQA2026!pass',adult:true,accepted_terms:true,accepted_privacy:true});await api('/onboarding',{city,interests:[],avatar:{color:'#41a8b8'},privacy:'City Mode',location_consent:false,analytics_consent:false});
 await p.goto(origin);await p.locator('.welcome-home').waitFor({timeout:60000});await p.locator('.destination-card.is-owned').first().click();await p.locator('.world-access-modal').getByRole('button',{name:/^Enter /}).click();await p.locator('.world-playing .world-canvas[data-ready=true]').waitFor({timeout:60000});
 fixture({city,users:[hostId,u.user.id]});await wait(1000);const direction=fixture({city}).direction;
 await hostPage.getByRole('button',{name:'walk',exact:true}).click();await input(...direction.map(n=>n*.6));await wait(700);await until(()=>peerFrames.at(-1)?.players.some(q=>q.id===hostId&&q.mode==='walk'&&q.speed>0),'remote walk');
 await input(...direction);await wait(850);await until(()=>peerFrames.at(-1)?.players.some(q=>q.id===hostId&&q.mode==='run'&&q.speed>0),'remote run');await input(0,0);await wait(1000);
 const final=(await hostApi('/world/'+city)).position,remote=peerFrames.at(-1).players.find(q=>q.id===hostId);check('remote sees walk and run and final authoritative position',Math.hypot(remote.x-final.x,remote.z-final.z)<.05);results.remote={final,remote:{x:remote.x,z:remote.z,mode:remote.mode,speed:remote.speed}};
 const event=await hostApi('/events',{title:'Local movement camera QA',description:'Disposable local test',city,starts_at:Date.now()/1000,communication_mode:'text',venue_experience_type:'auditorium',event_type:'Public Talk'});await hostApi('/events/'+event.id+'/state/start',{});await hostApi('/events/'+event.id+'/venue/enter',{});await api('/events/'+event.id+'/join',{});await api('/events/'+event.id+'/venue/enter',{});
 await p.locator('.in-auditorium .world-canvas[data-ready=true]').waitFor({timeout:60000});await wait(2000);check('real WebGL auditorium',await p.locator('.world-canvas canvas').count()>0&&await p.locator('.world-fallback').count()===0);
 const avatar=(await api('/world/'+city)).position,focus={x:Math.max(-.5,Math.min(.5,avatar.x)),y:(avatar.y||0)+1.7,z:Math.max(-4.5,Math.min(4.3,avatar.z-6))};
 const camera=()=>p.evaluate(()=>window.__qaCamera);const distance=pos=>Math.hypot(pos.x-focus.x,pos.y-focus.y,pos.z-focus.z);await until(async()=>!!await camera(),'rendered camera');
 const before=await camera();await p.mouse.move(600,350);await p.mouse.down();await p.mouse.move(650,350,{steps:10});await p.mouse.up();await wait(900);const after=await camera();
 const yaw=v=>v.yaw;check('small drag gives controlled camera angle',Math.abs(yaw(after)-yaw(before))>.025&&Math.abs(yaw(after)-yaw(before))<.09);check('drag does not change rendered camera distance',Math.abs(distance(after)-distance(before))<.03);
 await p.screenshot({path:path.join(out,'camera-desktop.jpg')});await p.mouse.wheel(0,-100);await wait(700);const zoomed=await camera();check('wheel explicitly zooms',distance(zoomed)<distance(after)-.5);
 for(const width of [390,820]){
  const spot=(await api('/world/'+city)).position;Object.assign(focus,{x:Math.max(-.5,Math.min(.5,spot.x)),y:(spot.y||0)+1.7,z:Math.max(-4.5,Math.min(4.3,spot.z-6))});
  await p.setViewportSize({width,height:844});await p.evaluate(()=>window.dispatchEvent(new Event('pulse-reset-camera')));await until(async()=>{const v=await camera();return Math.abs(distance(v)-10)<.002&&Math.abs(yaw(v))<.002},'settled camera reset');
  const session=await c.newCDPSession(p),send=(type,touchPoints)=>session.send('Input.dispatchTouchEvent',{type,touchPoints});
  const touchY=await p.evaluate(()=>[400,450,500,300].find(y=>[130,140,180,220,240,250].every(x=>document.elementFromPoint(x,y)?.tagName==='CANVAS')));assert.ok(touchY,'Unobstructed canvas row');
  const a=await camera();await send('touchStart',[{x:180,y:touchY,id:1}]);await send('touchMove',[{x:220,y:touchY,id:1}]);await send('touchEnd',[]);await wait(700);const b=await camera();console.log('touch measurement',width,{a,b,deltaYaw:yaw(b)-yaw(a),distanceA:distance(a),distanceB:distance(b)});check(width+' one finger rotates without zoom',Math.abs(distance(a)-distance(b))<.03&&Math.abs(yaw(b)-yaw(a))>.03);
  await send('touchStart',[{x:140,y:touchY,id:1},{x:240,y:touchY,id:2}]);await send('touchMove',[{x:130,y:touchY,id:1},{x:250,y:touchY,id:2}]);await send('touchEnd',[]);await wait(700);const pinched=await camera();check(width+' pinch zooms without orbit',distance(pinched)<distance(b)-.5&&Math.abs(yaw(pinched)-yaw(b))<.03);
  const stick=await p.locator('.mobile-joystick').boundingBox();const inputStart=peerFrames.at(-1)?.position;await send('touchStart',[{x:stick.x+stick.width*.75,y:stick.y+stick.height*.5,id:1}]);await wait(500);await send('touchEnd',[]);await wait(500);const stickCamera=await camera();check(width+' joystick does not rotate camera',Math.abs(yaw(stickCamera)-yaw(pinched))<.03);
  await p.screenshot({path:path.join(out,'camera-'+width+'.jpg')});await session.detach();
 }
 await wait(1000);const uiBefore=await camera();await p.getByRole('button',{name:'Event controls',exact:true}).click();await p.getByRole('button',{name:'Close panel',exact:true}).waitFor();const panel=await p.locator('.drawer').boundingBox();assert.ok(panel);
 await p.mouse.move(panel.x+panel.width/2,panel.y+180);await p.mouse.down();await p.mouse.move(panel.x+panel.width/2+25,panel.y+250,{steps:5});await p.mouse.up();await p.mouse.wheel(0,200);await wait(600);const uiAfter=await camera();check('event panel drag and scroll do not rotate or zoom camera',Math.abs(uiAfter.yaw-uiBefore.yaw)<.02&&Math.hypot(uiAfter.x-uiBefore.x,uiAfter.y-uiBefore.y,uiAfter.z-uiBefore.z)<.05);await p.getByRole('button',{name:'Close panel',exact:true}).click();
 check('camera browser has no runtime errors',errors.length===0);results.camera={before,after,zoomed,focus};await c.close();
 }catch(e){if(cameraPage){await cameraPage.screenshot({path:path.join(out,'camera-failure.jpg')}).catch(()=>{});fs.writeFileSync(path.join(out,'camera-failure.txt'),await cameraPage.locator('body').innerText().catch(()=>''))}throw e}finally{await browser.close()}
}
main().catch(e=>{console.error(e);process.exitCode=1});
