/* Actual production-build UI against the existing disposable property-browser CI database. */
const assert=require('node:assert/strict'),fs=require('node:fs'),{execFileSync}=require('node:child_process');
const {chromium}=require((process.env.QA_NODE_MODULES||process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES)+'/playwright');
const origin='http://127.0.0.1:3173',out=process.env.QA_OUTPUT||'/tmp/recovery-browser-evidence';
const checks=[],errors=[],failures=[];let browser;
const record=value=>{checks.push(value);console.log('PASS',value)};
async function main(){
 assert.equal(process.env.APP_ENV,'test');assert.match(process.env.DATABASE_URL||'',/^sqlite:.*property-browser-/);
 fs.mkdirSync(out,{recursive:true});
 browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const people=[];
 for(let i=0;i<3;i++){
  const ctx=await browser.newContext({viewport:{width:1280,height:900},hasTouch:true}),page=await ctx.newPage(),frames=[];
  page.setDefaultTimeout(15000);page.setDefaultNavigationTimeout(30000);
  page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=500)failures.push({url:r.url(),status:r.status()})});
  page.on('websocket',ws=>ws.on('framereceived',f=>{try{const v=JSON.parse(String(f.payload));if(['state','motion'].includes(v.type)){frames.push(v);if(frames.length>150)frames.shift()}}catch{}}));
  const api=async(path,data,method=data?'POST':'GET')=>{const r=await ctx.request.fetch(origin+'/api'+path,{method,data,headers:{Origin:origin,'X-Pulse-Client':'web'}});assert(r.ok(),path+' '+await r.text());return r.json()};
  const username='recovery'+i+Date.now().toString(36),account=await api('/auth/register',{username,email:username+'@example.test',password:'Local-Recovery-2026!acceptance',confirm_password:'Local-Recovery-2026!acceptance',adult:true,accepted_terms:true,accepted_privacy:true});
  await api('/onboarding',{city:'london',interests:[],avatar:{},privacy:'City Mode',location_consent:false,analytics_consent:false});
  people.push({ctx,page,api,frames,id:account.user.id,username});
 }
 const [host,guest,admin]=people;
 // Only local account privilege is provisioned. No wallet or position fixture.
 execFileSync(process.env.QA_PYTHON||'python',['-c',"import os,sys;assert os.environ['APP_ENV']=='test' and 'property-browser-' in os.environ['DATABASE_URL'];from backend.api.main import app;from backend.api.db import SessionLocal;from backend.api.models import User;db=SessionLocal();u=db.get(User,sys.argv[1]);assert u.email.endswith('@example.test');u.role='super_admin';db.commit()",admin.id]);
 await require('../../infrastructure/gcp/seating-acceptance.cjs')({host,guest,origin,out,record});
 console.log('Checking admin');const a=admin.page;await a.goto(origin+'/eluvathingal');await a.getByRole('button',{name:'Users',exact:true}).click();
 await a.getByLabel('Search username, email or ID').fill(guest.username);
 await a.getByRole('button',{name:'View user',exact:true}).click();await a.locator('.ops-kpis').getByText('Spendable XP',{exact:true}).waitFor();
 await a.getByRole('button',{name:'properties',exact:true}).click();await a.getByText('No recorded activity in this view.',{exact:true}).waitFor();
 await a.getByRole('button',{name:'profile',exact:true}).click();
 await a.getByLabel('Display name',{exact:true}).fill('Recovered profile');await a.getByLabel('Documented reason',{exact:true}).fill('Local browser acceptance profile correction');
 a.once('dialog',d=>d.accept());await a.getByRole('button',{name:'Review and save profile'}).click();
 await a.getByText('Profile correction saved and recorded in the audit log.').waitFor();
 assert.equal((await guest.api('/me')).profile.display_name,'Recovered profile');
 for(const [width,height]of [[1280,900],[390,844],[820,1180]]){
  await a.setViewportSize({width,height});assert.equal(await a.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  const fields=await a.locator('.operator-users input,.operator-users textarea,.operator-users select').evaluateAll(es=>es.filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.left<0||r.right>innerWidth+1)}).length);assert.equal(fields,0);
  if(width===390){
   const nav=a.getByRole('navigation',{name:'Administration'});
   if(await a.getByRole('button',{name:'Toggle admin navigation'}).getAttribute('aria-expanded')==='false')await a.getByRole('button',{name:'Toggle admin navigation'}).click();
   assert.equal(await nav.locator('button').evaluateAll(es=>es.filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.left<0||r.right>innerWidth+1)}).length),0);
   assert.equal(await nav.evaluate(e=>e.scrollWidth>e.clientWidth+1),false);
   await a.screenshot({path:out+'/admin-navigation-mobile.png'});
   await a.getByRole('button',{name:'Toggle admin navigation'}).click();
  }
  await a.getByLabel('Display name',{exact:true}).scrollIntoViewIfNeeded();
  await a.screenshot({path:out+'/admin-profile-'+width+'.png'});
 }
 record('Real user directory, property detail, audited profile edit and desktop/mobile/tablet layout');
 await a.setViewportSize({width:1280,height:900});await a.getByRole('button',{name:'wallet',exact:true}).click();
 await a.getByLabel('Amount',{exact:true}).fill('7');await a.getByLabel('Documented reason',{exact:true}).fill('Local browser audited XP acceptance');
 const original=await guest.api('/wallet');a.once('dialog',d=>d.accept());await a.getByRole('button',{name:'Review and confirm adjustment'}).click();await a.getByRole('status').filter({hasText:'Recorded transaction'}).waitFor();
 const after=await guest.api('/wallet');assert.equal(after.xp,original.xp+7);assert.equal(after.credits,original.credits);
 await a.getByRole('button',{name:'audit',exact:true}).click();await a.getByText('wallet.adjusted',{exact:true}).waitFor();record('Audited XP correction preserves PC balance');
 assert.deepEqual(errors,[]);assert.deepEqual(failures,[]);
 fs.writeFileSync(out+'/recovery-results.json',JSON.stringify({scope:'disposable local database, real browser and backend, software WebGL; not staging acceptance',checks,errors,failures},null,2));
 console.log(JSON.stringify({status:'PASS',checks}));
}
main().catch(async e=>{console.error(e);if(browser)for(const[i,ctx]of browser.contexts().entries())for(const page of ctx.pages()){await page.screenshot({path:out+'/recovery-failure-'+i+'.png'}).catch(()=>{});fs.writeFileSync(out+'/recovery-failure-'+i+'.txt',await page.locator('body').innerText().catch(()=>''));}process.exitCode=1}).finally(async()=>{await browser?.close()});
