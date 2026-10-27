/* Local-only real frontend/backend test; uses disposable test DB, never staging credentials. */
const assert=require('assert/strict');
const {chromium}=require((process.env.QA_NODE_MODULES||process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES)+'/playwright');
const {authenticateAndEnter}=require('../browser-flow.cjs');
const {act,inspectControl,expectedAnonymous}=require('../browser-ui.cjs');
const origin=process.env.QA_AUTH_ORIGIN;
assert.match(origin||'',/^http:\/\/127\.0\.0\.1:\d+$/,'Explicit local test server required');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,label,timeout=60000){const end=Date.now()+timeout;while(Date.now()<end){if(await fn())return true;await wait(100)}throw Error(label+' timed out')}
(async()=>{const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM,args:['--no-sandbox','--disable-dev-shm-usage','--disable-webgl']});const contexts=[];try{
 const users=[];
 for(const [index,width] of [[0,1100],[1,390]]){
  const context=await browser.newContext({viewport:{width,height:844},isMobile:width===390,hasTouch:width===390});contexts.push(context);
  const page=await context.newPage(),states=[],u={page,context,states,touch:width===390,authExpected:false};page.setDefaultTimeout(60000);
  page.on('websocket',ws=>ws.on('framereceived',frame=>{try{const d=JSON.parse(frame.payload);if(d.type==='state')states.push(d)}catch{}}));
  const failures=[];page.on('response',r=>{if(r.status()>=400)failures.push({status:r.status(),path:new URL(r.url()).pathname,expected:expectedAnonymous(r,u)})});
  u.api=async(route,data,method=data===undefined?'GET':'POST')=>{const r=await context.request.fetch(origin+'/api'+route,{method,data,headers:{Origin:origin,'X-Pulse-Client':'web'}});assert.ok(r.ok(),route+' HTTP '+r.status());return r.json()};
  try{
   await authenticateAndEnter(u,{origin,city:'milton-keynes',index,name:'localqa'+Date.now()+index,password:'Local-test-only-password-123!',reusable:false,until,setStage:s=>console.log('stage',s)});
   assert.ok(states.some(s=>s.city==='milton-keynes'));
   assert.ok(failures.filter(f=>f.path==='/api/me'&&f.status===401).every(f=>f.expected));
   console.log('Real local signup/onboarding/login/session/world entry PASS',width);users.push(u);
  }catch(e){console.error(u.failedControl);await page.screenshot({path:'/tmp/mindaam-auth-failure.png',mask:[page.locator('input,textarea')]});console.error((await page.locator('body').innerText()).slice(-3000));throw e}
 }

 const [a,b]=users;
 await a.api('/social/'+b.id+'/friend',{});await b.api('/social/'+a.id+'/accept',{});
 await act(a,a.page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'PEOPLE',exact:true}),'PEOPLE');
 await a.page.getByRole('heading',{name:'Your people',exact:true}).waitFor();
 await act(a,a.page.getByRole('tab',{name:'Friends',exact:true}),'Friends');
 await act(a,a.page.locator('.friend-card').filter({hasText:b.username}).getByRole('button',{name:'View profile',exact:true}),'View profile');
 const profile=a.page.getByRole('dialog',{name:'Player profile',exact:true});
 await act(a,profile.getByRole('button',{name:'Follow',exact:true}),'Follow');
 await profile.getByRole('button',{name:'Unfollow',exact:true}).waitFor();
 await act(a,profile.getByRole('button',{name:'Avatar',exact:true}),'Avatar tab');
 await act(a,profile.getByRole('button',{name:'Close profile',exact:true}),'Close profile');
 await act(a,a.page.getByRole('button',{name:'Close panel',exact:true}),'Close panel');
 console.log('Real local PEOPLE/Friends/View profile/Follow/Unfollow/Avatar tab controls PASS (WebGL rendering not tested)');
 const page=await browser.newPage(),u={page};
 await page.setContent('<main class="splash"><button hidden>Target</button><button id="target" disabled>Target</button><div id="cover" style="position:fixed;inset:0;z-index:5">Loading</div></main>');
 const target=page.getByRole('button',{name:'Target',exact:true});
 setTimeout(()=>page.evaluate(()=>{document.querySelector('main').className='app';document.querySelector('#target').disabled=false;document.querySelector('#cover').remove()}),200);
 await act(u,target,'delayed actionable target','click',undefined,2000);
 await page.evaluate(()=>{const cover=document.createElement('div');cover.className='blocking-overlay';cover.style='position:fixed;inset:0;z-index:5';document.body.append(cover)});
 await assert.rejects(act(u,target,'blocked target','click',undefined,300));
 assert.equal(u.failedControl.count,1);assert.equal(u.failedControl.elements[0].interceptor.className,'blocking-overlay');
 assert.equal(u.failedControl.elements[0].receivesPointer,false);assert.equal(u.failedControl.elements[0].tag,'BUTTON');
 await page.evaluate(()=>document.querySelector('.blocking-overlay').remove());
 await page.evaluate(()=>document.querySelector('#target').cloneNode(true)&&document.querySelector('#target').insertAdjacentHTML('afterend','<button>Target</button>'));
 await assert.rejects(act(u,target,'ambiguous target','click',undefined,300));
 assert.equal(u.failedControl.count,2);
 const r=(status,path,method='GET')=>({status:()=>status,url:()=>origin+path,request:()=>({method:()=>method})});
 assert.equal(expectedAnonymous(r(401,'/api/me'),{authExpected:false}),true);
 for(const [status,path,auth] of [[401,'/api/me',true],[403,'/api/me',false],[500,'/api/me',false],[401,'/api/other',false]])assert.equal(expectedAnonymous(r(status,path),{authExpected:auth}),false);
 console.log('Hydration/actionability/hidden duplicates/interceptor diagnostics/401 classification PASS');
}finally{for(const c of contexts){await c.request.delete(origin+'/api/me',{headers:{Origin:origin,'X-Pulse-Client':'web'}}).catch(()=>{});await c.close()}await browser.close()}})().catch(e=>{console.error(e.message);process.exitCode=1});
