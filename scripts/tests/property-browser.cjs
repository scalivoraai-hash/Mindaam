/* Exercise two real browser sessions against a disposable local build and database. */
const {chromium}=require((process.env.QA_NODE_MODULES||process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES)+'/playwright');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs');
const origin='http://127.0.0.1:3173';
const out=process.env.QA_OUTPUT||'/tmp/property-browser';
fs.mkdirSync(out,{recursive:true});
async function main(){
 assert.equal(process.env.APP_ENV,'test');
 assert.match(process.env.DATABASE_URL||'',/^sqlite:.*property-browser-/);
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const users=[];
  for(const [index,width] of [1280,390].entries()){
   const ctx=await browser.newContext({viewport:{width,height:850}}),page=await ctx.newPage();
   const post=async(path,data)=>{const r=await ctx.request.post(origin+'/api'+path,{data,headers:{Origin:origin,'X-Pulse-Client':'web'}});assert(r.ok(),path+' '+await r.text());return r.json()};
   const name='propertyqa'+index+Date.now().toString(36);
   const account=await post('/auth/register',{username:name,email:name+'@example.test',password:'Local-Property-Acceptance-93!',confirm_password:'Local-Property-Acceptance-93!',adult:true,accepted_terms:true,accepted_privacy:true});
   await post('/onboarding',{city:'london',interests:[],avatar:{},privacy:'City Mode',location_consent:false,analytics_consent:false});
   await post('/world/enter',{city:'london'});
   execFileSync(process.env.QA_PYTHON||'python',['-c',
    "import sys;from backend.api.db import SessionLocal;from backend.api.economy import credit;from backend.api.models import User;db=SessionLocal();u=db.get(User,sys.argv[1]);assert u.email.endswith('@example.test');credit(db,u.id,3500,'test','local-property-browser','fixture','xp');db.commit()",account.user.id]);
   await page.goto(origin);
   async function desk(){
    await page.getByRole('button',{name:'Account settings',exact:true}).click();
    await page.getByRole('button',{name:'🏡 My Properties',exact:true}).click();
    return page.getByRole('dialog',{name:'My Properties'});
   }
   users.push({ctx,page,desk,post});
  }
  const [seller,buyer]=users;
  await seller.page.locator('.destination-card.is-owned').first().click();
  await seller.page.locator('.world-access-modal').getByRole('button',{name:/^Enter /}).click();
  await seller.page.locator('.world-canvas[data-ready="true"] canvas').first().waitFor({timeout:60000});
  await seller.page.getByRole('button',{name:'🏡 Nearby property',exact:true}).click();
  const panel=seller.page.getByRole('dialog',{name:'My Properties'});
  const headline=panel.getByRole('heading',{level:3});
  await panel.getByRole('button',{name:/MAKE IT MINE/}).click();
  await panel.getByRole('button',{name:'Confirm purchase'}).click();
  await panel.getByText(/Congratulations! You’re now a property owner!/).waitFor();
  const sign='Sera Villa QA';
  await panel.getByLabel('Name my property').fill(sign);
  await panel.getByRole('button',{name:'Save and publish'}).click();
  await panel.getByText('Property published.').waitFor();
  assert.equal(await headline.innerText(),sign);
  const snapshot=await (await buyer.ctx.request.get(origin+'/api/world/london')).json();
  assert(snapshot.properties.some(row=>row.name===sign&&row.owned),'Nearby second account receives persistent owner nameboard');

  await seller.page.screenshot({path:out+'/owner-studio.png'});
  const second=await buyer.desk();await second.getByRole('button',{name:new RegExp(sign)}).click();
  await second.getByLabel('Your XP offer').fill('2500');await second.getByRole('button',{name:'Make an XP offer'}).click();
  await second.getByText('Offer delivered to the owner.').waitFor();
  await panel.getByRole('button',{name:'Offers',exact:true}).click();
  await panel.getByRole('button',{name:'Accept',exact:true}).click();
  await panel.getByText(/accepted · Incoming/).waitFor();
  await buyer.page.reload();const after=await buyer.desk();
  await after.getByRole('button',{name:'Portfolio',exact:true}).click();
  await after.locator('button[class*="card"]').first().click();
  await after.getByText('Your property',{exact:false}).first().waitFor();
  assert.equal(await buyer.page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  await buyer.page.screenshot({path:out+'/mobile-owner.png'});
  const ledger=async(ctx)=>(await (await ctx.request.get(origin+'/api/properties/history')).json()).map(t=>[t.action,t.xp]);
  assert.deepEqual(await ledger(seller.ctx),[['sold',2500],['acquired',2000]]);
  assert.deepEqual(await ledger(buyer.ctx),[['acquired',2500]]);
  console.log('PASS: desktop claim, confirmation, naming, mobile offer, seller acceptance, portfolio persistence and both transaction histories');
 }finally{await browser.close()}
}
main().catch(e=>{console.error(e);process.exitCode=1});
