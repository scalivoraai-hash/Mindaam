/* Real browser acceptance against an isolated local database, never staging funds. */
const {chromium}=require((process.env.QA_NODE_MODULES||process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES)+'/playwright');
const fs=require('fs'),assert=require('assert/strict'),{spawn,execFileSync}=require('child_process');
const root=require('path').resolve(__dirname,'../..'),out=process.env.QA_OUTPUT||'/tmp/mindaam-admin2-browser',python=process.env.QA_PYTHON||'python3';fs.mkdirSync(out,{recursive:true});
const env={...process.env,APP_ENV:'local',PUBLIC_ORIGIN:'http://127.0.0.1:3000',DATABASE_URL:'sqlite:////tmp/mylil-multi-admin2-'+Date.now()+'.db'};
for(const k of ['SUPER_ADMIN_EMAIL','SUPER_ADMIN_USERNAME','SUPER_ADMIN_INITIAL_PASSWORD','STRIPE_SECRET_KEY','STRIPE_WEBHOOK_SECRET','LIVEKIT_API_KEY','LIVEKIT_API_SECRET'])delete env[k];
execFileSync(python,['-m','scripts.tests.multiplayer_fixture','init','{}'],{cwd:root,env});
const children=[spawn(python,['-m','uvicorn','backend.api.main:app','--host','127.0.0.1','--port','8000'],{cwd:root,env,stdio:['ignore',fs.openSync(out+'/api.log','w'),fs.openSync(out+'/api-error.log','w')]}),spawn(process.execPath,['node_modules/next/dist/bin/next','start','apps/consumer-web','--hostname','127.0.0.1'],{cwd:root,env,stdio:['ignore',fs.openSync(out+'/web.log','w'),fs.openSync(out+'/web-error.log','w')]})];
process.on('exit',()=>children.forEach(p=>p.kill()));
(async()=>{
 for(let i=0;i<90;i++){try{if((await fetch(env.PUBLIC_ORIGIN)).ok&&(await fetch('http://127.0.0.1:8000/api/health')).ok)break}catch{}await new Promise(r=>setTimeout(r,1000))}
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM||'/tmp/mindaam-chromium/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}}),page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const contrastReports=[];const capture=page.screenshot.bind(page);page.screenshot=async opts=>{const check=await page.evaluate(()=>{const root=document.querySelector('.drawer')||document.querySelector('.ops-main')||document.querySelector('.welcome-home')||document.body;const rgb=s=>{const a=s.match(/[\d.]+/g)?.map(Number);return a&&a.length>=3?[a[0],a[1],a[2],a[3]??1]:[0,0,0,0]};const blend=(a,b)=>a.slice(0,3).map((v,i)=>v*a[3]+b[i]*(1-a[3]));const lum=c=>c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);let checked=0,gradients=0;const failures=[];for(const el of root.querySelectorAll('*')){if(!(el instanceof HTMLElement)||!el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})||!Array.from(el.childNodes).some(n=>n.nodeType===3&&n.textContent.trim()))continue;const r=el.getBoundingClientRect();if(r.bottom<0||r.top>innerHeight||r.width===0)continue;const cs=getComputedStyle(el);let chain=[],n=el,gradient=false;while(n){const style=getComputedStyle(n);if(style.backgroundImage!=='none')gradient=true;const layer=rgb(style.backgroundColor);chain.push(layer);if(layer[3]===1)break;n=n.parentElement}if(gradient){gradients++;continue}let bg=[255,255,255];for(const c of chain.reverse())bg=blend(c,bg);const fg=blend(rgb(cs.color),bg),a=lum(fg),b=lum(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);const large=parseFloat(cs.fontSize)>=24||(parseFloat(cs.fontSize)>=18.66&&Number(cs.fontWeight)>=700);checked++;if(ratio<(large?3:4.5))failures.push({text:el.textContent.trim().slice(0,65),selector:el.tagName+'.'+el.className,color:cs.color,bg,ratio})}return {checked,gradients,failures}});contrastReports.push({screen:opts.path,...check});fs.writeFileSync(out+'/contrast.json',JSON.stringify(contrastReports,null,2));return capture(opts)};
 const request=async(path,data)=>{const r=await ctx.request.fetch(env.PUBLIC_ORIGIN+'/api'+path,{method:data?'POST':'GET',data,headers:{Origin:env.PUBLIC_ORIGIN,'X-Pulse-Client':'web'}});assert(r.ok(),path+': '+await r.text());return r.json()};
 const registered=await request('/auth/register',{username:'local_operator',email:'local-operator@example.test',password:'LocalBrowserQA2026!pass',confirm_password:'LocalBrowserQA2026!pass',adult:true,accepted_terms:true,accepted_privacy:true});
 assert.equal((await ctx.request.get(env.PUBLIC_ORIGIN+'/api/super-admin/overview')).status(),403);
 execFileSync(python,['-c',`
from backend.api import main
from backend.api.db import SessionLocal
from backend.api.models import User,Event
import sys,time
with SessionLocal.begin() as db:
 owner=db.get(User,sys.argv[1]);owner.role='super_admin'
 for i in range(32):
  db.add(Event(id='local-event-%03d'%i,host_id=owner.id,title='Local acceptance event %03d'%i,city='london',starts_at=time.time()+3600,status='scheduled',venue_mode='virtual_auditorium',created_at=time.time()-i*86400))
`,registered.user.id],{cwd:root,env});
 await page.goto(env.PUBLIC_ORIGIN+'/eluvathingal');await page.getByRole('heading',{name:'Your platform, in perspective.',exact:true}).waitFor();
 assert.equal((await request('/super-admin/overview')).kpis.total_events,32);
 const nav=async(name)=>{const n=page.locator('.ops-layout>nav');if(!await n.isVisible())await page.getByRole('button',{name:'Toggle admin navigation'}).click();await n.getByRole('button',{name,exact:true}).click();await page.locator('.ops-main> .section-head h1').filter({hasText:name}).waitFor();};
 await nav('Events');await page.getByRole('button',{name:'View details',exact:true}).first().waitFor();
 await page.getByLabel('Rows per page').selectOption('10');await page.getByText('Page 1 of 4 · 32 records',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Next',exact:true}).click();await page.getByText('Page 2 of 4 · 32 records',{exact:true}).waitFor();
 await page.getByLabel('Search records').fill('event 007');await page.getByRole('button',{name:'Search',exact:true}).click();await page.getByText('Page 1 of 1 · 1 records',{exact:true}).waitFor();
 await page.getByRole('button',{name:'View details',exact:true}).click();await page.getByRole('heading',{name:'Local acceptance event 007',exact:true}).waitFor();
 for(const tab of ['Participants','Tickets','Venue / Reservation','Schedule','Organiser','Overview']){await page.getByRole('navigation',{name:'Event detail tabs'}).getByRole('button',{name:tab,exact:true}).click();await page.locator('.ops-detail-page').waitFor();}
 await nav('Users');await page.getByRole('columnheader',{name:'Username',exact:true}).waitFor();await page.getByRole('button',{name:'View user',exact:true}).first().click();await page.getByRole('button',{name:'wallet',exact:true}).click();await page.getByRole('heading',{name:'Audited wallet adjustment'}).waitFor();
 const screens=['Overview','Live Operations','Users','Events','Revenue','Reservations','Advertising enquiries','Advertisements','Credit packs','Subscriptions','Audit','World demand','Missions','XP Activity','Payments','Transport','Stops','Buildings'];let captures=0;
 for(const theme of ['light','dark']){
  await page.evaluate(t=>{localStorage.setItem('mindaam-theme',t);document.documentElement.dataset.theme=t;window.dispatchEvent(new Event('mindaam-theme-change'))},theme);
  for(const [width,height] of [[1440,1000],[768,1024],[390,844]]){
   await page.setViewportSize({width,height});
   for(const name of screens){await nav(name);await page.waitForFunction(()=>!document.querySelector('.ops-main [role=status]')?.textContent?.includes('Loading'));
    assert.equal(await page.locator('.ops-main [role=alert]').count(),0,`${theme} ${width} ${name}`);
    assert(await page.evaluate(()=>{const h=document.querySelector('.ops-enterprise>header'),logo=h.querySelector('.brand-artwork').getBoundingClientRect();return Array.from(h.children).filter(e=>!e.matches('.brand')&&e.getBoundingClientRect().width).every(e=>{const r=e.getBoundingClientRect();return r.right<=logo.left||r.left>=logo.right||r.bottom<=logo.top||r.top>=logo.bottom})}),'Header logo overlaps another control');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Viewport overflow: '+name+' '+width);
    await page.screenshot({path:`${out}/${theme}-${width}-${name.replaceAll(' ','-')}.png`,fullPage:false});captures++;
    if(name==='Overview'){await page.locator('.ops-charts').scrollIntoViewIfNeeded();await page.screenshot({path:`${out}/${theme}-${width}-Charts.png`});captures++;await page.evaluate(()=>scrollTo(0,0))}
    if(name==='Users'){await page.getByRole('button',{name:'View user',exact:true}).first().click();await page.getByRole('button',{name:'wallet',exact:true}).waitFor();await page.screenshot({path:`${out}/${theme}-${width}-User-Details.png`});captures++}
    if(name==='Events'){await page.getByRole('button',{name:'View details',exact:true}).first().click();await page.getByRole('heading',{name:/Local acceptance event/}).waitFor();await page.screenshot({path:`${out}/${theme}-${width}-Event-Details.png`});captures++}
   }
  }
 }
 assert.deepEqual(errors,[]);assert(contrastReports.every(r=>r.checked>0),'Each capture must include measured text contrast');assert.deepEqual(contrastReports.flatMap(r=>r.failures),[],'Solid surface text contrast');fs.writeFileSync(out+'/result.json',JSON.stringify({localOnly:true,captures,errors,pagination:true,search:true,eventDetail:true,ordinaryDenial:true},null,2));console.log('PASS',captures,'local theme/viewport captures, pagination, search, details and role protection.');await browser.close();children.forEach(p=>p.kill());
})().catch(e=>{console.error(e);process.exit(1)});
