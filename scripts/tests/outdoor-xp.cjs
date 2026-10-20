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
 // Prove the 3x release contract using the real handler and controlled server ticks.
 execFileSync(python,['-m','pytest','backend/tests/test_outdoor_speed_contract.py','-q'],{cwd:root,env:{...env,APP_ENV:'test'},stdio:'inherit'});
 check('controlled server ticks preserve 3x outdoor contract',true);
 const diagnostics={errors:[],requests:[],sockets:[],processes:[]};let page,browser;
 const children=[];
 try{
 for(const [bin,args,log] of [[python,process.env.QA_API_ROOT?['-m','uvicorn','backend.api.main:app','--host','127.0.0.1','--port','8000']:['-m','scripts.tests.motion_profile_server'],'api'],[process.execPath,['node_modules/next/dist/bin/next','start','apps/consumer-web','--hostname','127.0.0.1','--port','3000'],'web']]){const fd=fs.openSync(path.join(out,log+'.log'),'w');const child=spawn(bin,args,{cwd:log==='api'?(process.env.QA_API_ROOT||root):root,env:{...env,PUBLIC_ORIGIN:origin},stdio:['ignore',fd,fd]});children.push(child);child.on('exit',(code,signal)=>diagnostics.processes.push({name:log,code,signal}));fs.closeSync(fd);if(log==='api')await until(async()=>{if(child.exitCode!==null)throw Error('Backend exited before readiness');try{return (await fetch('http://127.0.0.1:8000/api/health',{signal:AbortSignal.timeout(2000)})).status===200}catch{return false}},'backend readiness (HTTP 200)')}
 await until(async()=>{try{return (await fetch(origin+'/api/health',{signal:AbortSignal.timeout(2000)})).ok}catch{return false}},'application startup');
 browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM||'/tmp/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-webgl','--disable-background-timer-throttling']});
 const city=process.env.QA_CITY||'milton-keynes',route=fixture({city}),context=await browser.newContext({viewport:{width:Number(process.env.QA_WIDTH||1440),height:900},hasTouch:Number(process.env.QA_WIDTH||1440)<1000});page=await context.newPage();
 await page.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){return /webgl/.test(kind)?null:get.call(this,kind,...args)};window.__qaLongTasks=[];new PerformanceObserver(list=>{for(const e of list.getEntries())window.__qaLongTasks.push({start:e.startTime,duration:e.duration})}).observe({type:'longtask',buffered:true})});
 const api=async(url,data)=>{const r=await context.request.fetch(origin+'/api'+url,{method:data===undefined?'GET':'POST',data,headers:{Origin:origin,'X-Pulse-Client':'web'}});assert.ok(r.ok(),url+' '+await r.text());return r.json()};
 const errors=diagnostics.errors;page.on('pageerror',e=>errors.push(e.message));
 page.on('response',r=>{if(r.url().includes('/api/'))diagnostics.requests.push({at:Date.now(),path:new URL(r.url()).pathname,status:r.status()})});
 page.on('requestfailed',r=>diagnostics.requests.push({at:Date.now(),path:new URL(r.url()).pathname,error:r.failure()?.errorText}));
 const frames=[],sent=new Map();page.on('websocket',ws=>{diagnostics.sockets.push({at:Date.now(),event:'created',url:ws.url()});ws.on('close',()=>diagnostics.sockets.push({at:Date.now(),event:'close'}));ws.on('socketerror',error=>diagnostics.sockets.push({at:Date.now(),event:'error',error}));ws.on('framesent',f=>{try{const d=JSON.parse(f.payload.toString());if(d.type==='input')sent.set(d.seq,Date.now())}catch{}});ws.on('framereceived',f=>{try{const d=JSON.parse(f.payload.toString());if(!diagnostics.sockets.some(e=>e.type===d.type))diagnostics.sockets.push({at:Date.now(),event:'frame',type:d.type,city:d.city,movement_transport:d.movement_transport});if(d.type==='motion'||d.type==='state')frames.push({at:Date.now(),roundTripMs:d.type==='motion'&&sent.has(d.seq)?Date.now()-sent.get(d.seq):undefined,...d})}catch{}})});
 const input=(x,z)=>page.evaluate(([x,z])=>window.dispatchEvent(new CustomEvent('pulse-drive-input',{detail:[x,z]})),[x,z]);
 const position=()=>page.locator('.world-minimap svg g[transform]').evaluate(el=>el.getAttribute('transform').match(/-?[\d.]+/g).map(Number));
 // Keep the actual preview renderer/input path. Place only the public fixture response on a measured real road.
 await page.route('**/api/world-preview/'+city,async r=>{const response=await r.fetch(),v=await response.json();v.position={...v.position,x:route.x,z:route.z};await r.fulfill({response,json:v})});
 await page.goto(origin+'/explore');if(city!=='milton-keynes')await page.locator('#preview-city').selectOption(city);
 await page.locator('.world-canvas[data-ready=true]').waitFor();
 async function measure(name,direction=route.direction){
   const frameStart=frames.length;
   const {a,b,elapsed,longTasks}=await page.evaluate(async ({direction,target})=>{
    const pos=()=>document.querySelector('.world-minimap svg g[transform]').getAttribute('transform').match(/-?[\d.]+/g).map(Number);
    const a=pos(),at=performance.now();window.dispatchEvent(new CustomEvent('pulse-drive-input',{detail:direction}));
    while(Math.hypot(pos()[0]-a[0],pos()[1]-a[1])<target){if(performance.now()-at>60000)throw Error('Route timeout');await new Promise(r=>setTimeout(r,10))}window.dispatchEvent(new CustomEvent('pulse-drive-input',{detail:[0,0]}));const elapsed=(performance.now()-at)/1000;
    await new Promise(r=>setTimeout(r,350));return {a,b:pos(),elapsed,longTasks:window.__qaLongTasks.filter(e=>e.start+e.duration>=at)};
   },{direction,target:Math.min(180,route.length*.7)});
   const measured=frames.slice(frameStart).filter(f=>f.type==='motion'),latencies=measured.map(f=>f.roundTripMs).filter(Number.isFinite).sort((a,b)=>a-b);
   const row={name,distance:Math.hypot(b[0]-a[0],b[1]-a[1]),seconds:elapsed,start:a,end:b,longTasks};if(latencies.length)row.acknowledgements={count:latencies.length,p50Ms:latencies[Math.floor(latencies.length*.5)],p95Ms:latencies[Math.floor(latencies.length*.95)],maxMs:latencies.at(-1),maxServerGapMs:Math.max(...measured.slice(1).map((f,i)=>(f.position.last_move-measured[i].position.last_move)*1000))};row.mps=row.distance/elapsed;results.speeds.push(row);console.log(JSON.stringify(row));return row;
 }
 const name='motion'+Date.now();const user=await api('/auth/register',{email:name+'@example.test',username:name,password:'LocalMotionQA2026!pass',confirm_password:'LocalMotionQA2026!pass',adult:true,accepted_terms:true,accepted_privacy:true});
 await api('/onboarding',{city,interests:[],avatar:{color:'#e58a50'},privacy:'City Mode',location_consent:false,analytics_consent:false});
 await page.goto(origin);await page.locator('.welcome-home').waitFor();await page.locator('.destination-card.is-owned').first().click();await page.locator('.world-access-modal').getByRole('button',{name:/^Enter /}).click();await page.locator('.world-playing').waitFor();await until(()=>frames.some(f=>f.movement_transport),'socket');
 if(process.env.QA_CAMERA_ONLY){await cameraAndPeer(browser,api,user.user.id,city,page,input,frames);await keyboardRegression(page,frames);return}
 async function place(){fixture({city,users:[user.user.id]});await wait(900)}
 async function mode(value){const desktop=page.getByRole('button',{name:value,exact:true});if(await desktop.isVisible())await desktop.click();else{const toggle=page.locator('.mobile-run');if((await toggle.getAttribute('aria-pressed')==='true')!==(value==='run'))await toggle.click()}}
 results.city=city;results.viewport=Number(process.env.QA_WIDTH||1440);results.route=route;
 await place();await mode('walk');const walk=await measure('authenticated light walk',route.direction.map(n=>n*.6));
 await place();await mode('run');const run=await measure('authenticated explicit run');
 // Wall-clock m/s and acknowledgement delays remain diagnostics, not a speed-law gate.
 // Browser integration still has to deliver the selected mode and real authoritative movement.
 for(const [mode,row] of [['walk',walk],['run',run]]){
  check(mode+' authoritative movement reaches mapped target',row.distance>=Math.min(180,route.length*.7));
  check(mode+' selected mode reaches server',frames.some(f=>f.type==='motion'&&f.position?.mode===mode&&f.position.speed>0));
 }
 if(results.viewport<1000){
  const session=await context.newCDPSession(page);
  for(const [kind,strength] of [['walk',.6],['run',1]]){
   await place();await mode(kind);const box=await page.locator('.mobile-joystick').boundingBox();assert.ok(box);
   const frameStart=frames.length,a=await position(),at=Date.now();await session.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:box.x+box.width/2+route.direction[0]*strength*box.width*.36,y:box.y+box.height/2+route.direction[1]*strength*box.height*.36,id:1}]});
   await wait(1200);await session.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});const elapsed=(Date.now()-at)/1000;await wait(350);const b=await position(),mps=Math.hypot(b[0]-a[0],b[1]-a[1])/elapsed;
   results.speeds.push({name:'native touch '+kind,mps,seconds:elapsed});check('native touch '+kind+' authoritative movement',Math.hypot(b[0]-a[0],b[1]-a[1])>0&&frames.slice(frameStart).some(f=>f.type==='motion'&&f.position?.mode===kind&&f.position.speed>0));
  }
  await session.detach();
 }
 for(const kind of ['bike','car']){
  const placed=fixture({city,users:[user.user.id],kind});await wait(900);
  await page.evaluate(id=>window.dispatchEvent(new CustomEvent('pulse-city-action',{detail:{kind:'rental',data:{id}}})),placed.asset);await page.locator('.mobility-panel article').first().waitFor();
  const accept=page.getByRole('button',{name:'I accept this policy',exact:true});if(await accept.count())await accept.click();
  const listing=await api('/mobility'),asset=listing.assets.find(a=>a.id===placed.asset);
  const card=page.locator('.mobility-panel article').filter({hasText:asset.name}).filter({hasText:'0 m away'}).first();
  await until(async()=>await card.count()>0,'nearby rental card');
  check(kind+' XP label',asset.currency==='xp'&&(await card.innerText()).includes(asset.cost+' XP')&&!(await card.innerText()).includes('Credits'));
  check(kind+' no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:path.join(out,kind+'-xp-price.jpg')});
  const before=await api('/wallet');let submissions=0;const count=r=>{if(r.url().endsWith('/rent')&&r.method()==='POST')submissions++};page.on('request',count);
  // A wallet read started before the purchase may arrive after its response.
  // The acknowledged server balance must win without a second wallet request.
  let releaseWallet;const walletHeld=new Promise(resolve=>{releaseWallet=resolve});let walletReads=0;
  await page.route('**/api/wallet',async r=>{walletReads++;await walletHeld;await r.fulfill({json:before})});
  await page.evaluate(()=>window.dispatchEvent(new Event('pulse-wallet-refresh')));
  await until(()=>walletReads===1,'old wallet request captured');
  try{
  await card.getByRole('button',{name:kind==='car'?'Rent & drive':'Rent & ride',exact:true}).click();
  await page.locator('.drive-controls').waitFor();page.off('request',count);
  const after=await api('/wallet');check(kind+' first tap single XP debit',submissions===1&&before.xp-after.xp===asset.cost&&before.credits===after.credits);
  await until(async()=>await page.locator('.topbar .balance').first().innerText().then(t=>t.startsWith(after.xp+' XP')),'rental header balance');
  releaseWallet();await wait(250);
  check(kind+' header shows server-confirmed XP',await page.locator('.topbar .balance').first().innerText().then(t=>t.startsWith(after.xp+' XP')));
  check(kind+' rental avoids redundant wallet read',walletReads===1);
  }finally{releaseWallet();await page.unroute('**/api/wallet')}
  // Keep the lease ended server-side while withholding its HTTP response. The
  // former input loop kept driving during this gap and showed 'No active vehicle'.
  let releaseExit;const exitHeld=new Promise(resolve=>{releaseExit=resolve});let exitEnded=false,exitRequests=0;
  await page.route('**/api/mobility/exit',async r=>{exitRequests++;const response=await r.fetch();exitEnded=true;await exitHeld;await r.fulfill({response})});
  try{
   await page.getByRole('button',{name:'Exit vehicle',exact:true}).click();
   check(kind+' exit acknowledges first tap',await page.getByRole('button',{name:'Exiting…',exact:true}).isDisabled());
   await until(()=>exitEnded,'exit committed on server');
   await wait(450);
   check(kind+' delayed exit has no movement error',await page.locator('.toast.error').count()===0);
  }finally{releaseExit()}
  await page.locator('.drive-controls').waitFor({state:'detached'});await wait(800);
  await page.unroute('**/api/mobility/exit');
  check(kind+' exit single request',exitRequests===1);
  check(kind+' exit stays on foot without stale errors',!(await api('/mobility')).rental&&await page.locator('.toast.error').count()===0);
 }
 await until(()=>Date.now()%30000<2500,'local bus boarding window',32000);
 const bus=JSON.parse(execFileSync(python,['-m','scripts.tests.multiplayer_fixture','bus',JSON.stringify({city,users:[user.user.id]})],{cwd:root,env,encoding:'utf8'}));
 await api('/growth/worlds/'+bus.destination+'/starter',{confirmed:true});await wait(1200);
 await page.evaluate(()=>window.dispatchEvent(new CustomEvent('pulse-city-action',{detail:{kind:'transit',data:{}}})));
 await page.locator('.departure-board article').first().waitFor();
 const board=await api('/transit/board/'+city),entry=board.routes.find(r=>r.id===bus.route),card=page.locator('.departure-board article').filter({hasText:entry.destination_name});
 check('bus XP fare label',entry.currency==='xp'&&(await card.innerText()).includes(entry.fare+' XP')&&!(await card.innerText()).includes('Credits'));
 check('bus no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 await page.screenshot({path:path.join(out,'bus-xp-fare.jpg')});
 const before=await api('/wallet');await card.getByRole('button',{name:'Buy ticket & board',exact:true}).click();await page.locator('.journey-status').waitFor();
 const after=await api('/wallet');check('bus first tap XP debit',before.xp-after.xp===entry.fare&&before.credits===after.credits);
 await until(async()=>await page.locator('.topbar .balance').first().innerText().then(t=>t.startsWith(after.xp+' XP')),'bus header balance');
 check('bus header shows server-confirmed XP',await page.locator('.topbar .balance').first().innerText().then(t=>t.startsWith(after.xp+' XP')));
 const retry=await api('/transit/board',{id:require('crypto').randomUUID(),vehicle_id:entry.vehicle_id,expected_fare:entry.fare,expected_currency:'xp'});
 const retried=await api('/wallet');check('bus retry cannot charge again',retry.duplicate&&retried.xp===after.xp&&retried.credits===after.credits);
 check('no browser errors',errors.length===0);
 await page.screenshot({path:path.join(out,'outdoor-xp.jpg')});
 }catch(error){
  results.failure=String(error.stack||error);
  if(page){diagnostics.visibleText=await page.locator('body').innerText().catch(()=>'<unavailable>');await page.screenshot({path:path.join(out,'failure.jpg')}).catch(()=>{});}
  fs.writeFileSync(path.join(out,'diagnostics.json'),JSON.stringify(diagnostics,null,2));console.error(JSON.stringify(diagnostics,null,2));
  for(const name of ['api','web']){const file=path.join(out,name+'.log');if(fs.existsSync(file))console.error(name+' log tail:\n'+fs.readFileSync(file,'utf8').split('\n').slice(-100).join('\n'));}
  throw error;
 }finally{fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));await browser?.close();for(const c of children)c.kill()}
}
main().catch(e=>{console.error(e);process.exitCode=1});
