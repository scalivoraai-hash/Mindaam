/* Local-only full-application renderer smoke. The profile response is explicitly a test fixture, never staging evidence. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),{spawn,execFileSync}=require('child_process');
const {chromium}=require((process.env.QA_NODE_MODULES||process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES)+'/playwright');
const root=path.resolve(__dirname,'../..'),origin='http://127.0.0.1:3000',python=process.env.QA_PYTHON||'python3',out=process.env.QA_OUTPUT||'/tmp/mindaam-movement-settings';fs.mkdirSync(out,{recursive:true});
const env={...process.env,APP_ENV:'local',PUBLIC_ORIGIN:origin,DATABASE_URL:'sqlite:////tmp/mylil-multi-speeds-'+Date.now()+'.db'};for(const k of ['STRIPE_SECRET_KEY','STRIPE_WEBHOOK_SECRET','LIVEKIT_API_KEY','LIVEKIT_API_SECRET','SUPER_ADMIN_EMAIL','SUPER_ADMIN_USERNAME','SUPER_ADMIN_INITIAL_PASSWORD'])delete env[k];
const fixture=d=>JSON.parse(execFileSync(python,['-m','scripts.tests.motion_fixture',JSON.stringify(d)],{cwd:root,env,encoding:'utf8'}));
const wait=ms=>new Promise(r=>setTimeout(r,ms)),checks=[],measurements=[],children=[],timing=[];let browser,playerPage;
const pass=name=>{checks.push(name);console.log('PASS',name)};
async function until(fn,label){const end=Date.now()+60000;while(Date.now()<end){if(await fn())return;await wait(100)}throw Error('Timed out: '+label)}
async function main(){
 execFileSync(python,['-m','scripts.tests.multiplayer_fixture','init'],{cwd:root,env});
 // Seed the full city inventory before timing readiness (cold local SQLite fixture).
 execFileSync(python,['-c',"import asyncio; from backend.api.main import app; exec('async def seed():\\n async with app.router.lifespan_context(app): pass'); asyncio.run(seed())"],{cwd:root,env});
 for(const [bin,args,name]of [[python,['-m','uvicorn','backend.api.main:app','--host','127.0.0.1','--port','8000'],'api'],[process.execPath,['node_modules/next/dist/bin/next','start','apps/consumer-web','--hostname','127.0.0.1'],'web']]){const fd=fs.openSync(out+'/'+name+'.log','w');children.push(spawn(bin,args,{cwd:root,env,stdio:['ignore',fd,fd]}))}
 await until(async()=>{try{return (await fetch(origin+'/api/health')).ok}catch{return false}},'startup');
 browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const player=await browser.newContext({viewport:{width:1440,height:900},hasTouch:true}),admin=await browser.newContext({viewport:{width:1280,height:900}}),p=await player.newPage(),a=await admin.newPage(),frames=[],errors=[];
 playerPage=p;await p.addInitScript(()=>{window.__movementTiming=[];const record=(type,extra={})=>{window.__movementTiming.push({type,time:Date.now(),...extra});if(window.__movementTiming.length>500)window.__movementTiming.shift()};for(const type of ['blur','focus','visibilitychange'])window.addEventListener(type,()=>record(type,{hidden:document.hidden}));if(PerformanceObserver.supportedEntryTypes.includes('longtask'))new PerformanceObserver(list=>{for(const entry of list.getEntries())record('longtask',{start:performance.timeOrigin+entry.startTime,duration:entry.duration})}).observe({type:'longtask',buffered:true})});for(const page of [p,a])page.on('pageerror',e=>errors.push(e.message));
 p.on('websocket',ws=>{ws.on('framesent',f=>{try{const d=JSON.parse(f.payload.toString());if(d.type==='input')timing.push({type:'sent',time:Date.now(),seq:d.seq,action:d.action,x:d.x,z:d.z})}catch{}});ws.on('framereceived',f=>{try{const d=JSON.parse(f.payload.toString());if(d.type==='motion'||d.type==='state')frames.push(d);if(d.type==='motion')timing.push({type:'ack',time:Date.now(),seq:d.seq,position:d.position,speed:d.rental?.speed,heading:d.rental?.heading,configuration:d.movement_config?.version})}catch{}})});
 const api=async(ctx,url,data,method=data?'POST':'GET')=>{const r=await ctx.request.fetch(origin+'/api'+url,{method,data,headers:{Origin:origin,'X-Pulse-Client':'web'}});assert(r.ok(),url+' '+await r.text());return r.json()};
 async function register(ctx,prefix){const username=prefix+Date.now().toString(36);return api(ctx,'/auth/register',{username,email:username+'@example.test',password:'LocalBrowserSpeedQA2026!pass',confirm_password:'LocalBrowserSpeedQA2026!pass',adult:true,accepted_terms:true,accepted_privacy:true})}
 const user=await register(player,'speedplayer'),owner=await register(admin,'speedadmin');
 await api(player,'/onboarding',{city:'milton-keynes',interests:[],avatar:{color:'#41a8b8'},privacy:'City Mode',location_consent:false,analytics_consent:false});
 execFileSync(python,['-c',"import os,sys;assert os.environ['APP_ENV']=='local' and os.environ['DATABASE_URL'].startswith('sqlite:////tmp/mylil-multi-speeds-');from backend.api.main import app;from backend.api.db import SessionLocal;from backend.api.models import User;\nwith SessionLocal.begin() as db:db.get(User,sys.argv[1]).role='super_admin'",owner.user.id],{cwd:root,env});

 // Count browser animation intervals containing a draw on the active world canvas.
 await p.addInitScript(()=>{
  window.__worldDraws=0;
  for(const method of ['drawElements','drawArrays','drawElementsInstanced','drawArraysInstanced']){
   const original=WebGL2RenderingContext.prototype[method];
   WebGL2RenderingContext.prototype[method]=function(...args){
    if(this.canvas.isConnected)window.__worldDraws++;
    return original.apply(this,args);
   };
  }
 });
 await p.route('**/api/visual-profile/milton-keynes',route=>route.fulfill({json:{city:'milton-keynes',profile:'cinematic-world-v1'}}));
 const assetResponses=[];p.on('response',r=>{if(r.url().includes('/assets/whitehouse/'))assetResponses.push({url:new URL(r.url()).pathname,status:r.status()})});
 const started=Date.now();await p.goto(origin);await p.locator('.welcome-home').waitFor();await p.locator('.destination-card.is-owned').first().click();await p.locator('.world-access-modal').getByRole('button',{name:/^Enter /}).click();await p.locator('.world-playing').waitFor();await p.locator('.world-canvas canvas').waitFor({timeout:60000});
 await until(()=>assetResponses.some(r=>r.url.endsWith('.glb')&&r.status===200),'cinematic asset loaded');
 const entryMs=Date.now()-started;await wait(3000);
 const metrics=[];
 for(const [width,height] of [[1280,900],[320,568],[375,812],[390,844],[430,932],[768,1024],[820,1180],[1024,768],[1180,820]]){
  await p.setViewportSize({width,height});await wait(800);
  assert(await p.locator('.world-canvas canvas').isVisible());
  const overflow=await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);assert.equal(overflow,false,'page overflow '+width);
  const sample=await p.evaluate(()=>new Promise(resolve=>{
   let last=performance.now(),draws=window.__worldDraws;
   const start=last, intervals=[];
   function frame(now){
    if(window.__worldDraws!==draws){intervals.push(now-last);last=now;draws=window.__worldDraws}
    if(now-start<2500){requestAnimationFrame(frame);return}
    intervals.sort((a,b)=>a-b);
    const quantile=q=>intervals.length?intervals[Math.floor((intervals.length-1)*q)]:null;
    resolve({sampleMs:now-start,drawnFrames:intervals.length,submittedFps:intervals.length*1000/(now-start),
     frameMedianMs:quantile(.5),frameP95Ms:quantile(.95),jsHeapBytes:performance.memory?.usedJSHeapSize??null});
   }
   requestAnimationFrame(frame);
  }));
  metrics.push({width,height,...sample});
  await p.screenshot({path:out+'/world-'+width+'x'+height+'.png'});
 }
 const downloads=await p.evaluate(()=>performance.getEntriesByType('resource').reduce((totals,entry)=>{
  totals.responses++;totals.transferBytes+=entry.transferSize;totals.encodedBodyBytes+=entry.encodedBodySize;return totals;
 },{responses:0,transferBytes:0,encodedBodyBytes:0}));
 assert.deepEqual(errors,[]);fs.writeFileSync(out+'/results.json',JSON.stringify({scope:'local full application with intercepted staging-profile response; software-rendered, not staging acceptance',entryMs,assetResponses,metrics,downloads,errors},null,2));
 console.log('PASS full application cinematic asset and nine viewport smoke checks');
}
main().catch(e=>{console.error(e);process.exitCode=1}).finally(async()=>{if(browser)await browser.close();for(const child of children)child.kill('SIGTERM')});
