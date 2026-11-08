/* Test the deployed HTTPS application using real signup XP and two actual mapped buildings. */
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {chromium}=require(process.env.QA_NODE_MODULES+'/playwright');
const release=JSON.parse(fs.readFileSync('deployment-result.json'));
const origin='https://mindaam-staging-qfrofqn4pq-nw.a.run.app';
assert.equal(release.environment,'staging');assert.equal(release.origin,origin);assert.equal(process.env.MINDAAM_PROJECT_ID,'mindaam');
assert.match(process.env.GITHUB_RUN_ID,/^\d+$/);
assert.equal(release.sha,process.env.RELEASE_SHA);
const evidence={seating_checks:[],sha:release.sha,revision:release.revision,image:release.image,cities:{},quotes_restored:false};
const out='gcp-evidence';fs.mkdirSync(out,{recursive:true});
const ids=[],users=[],originalQuotes={};
const quote=(action)=>execFileSync('gcloud',['run','jobs','execute','mindaam-migrate-staging','--project=mindaam','--region=europe-west2','--wait',
 '--args=-m,backend.api.staging_property_quotes,'+action+','+process.env.GITHUB_RUN_ID+','+ids.join(',')],{stdio:['ignore','ignore','inherit']});
async function main(){
 const browser=await chromium.launch({args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 let prepared=false;
 try{
  for(const [i,width] of [1280,390].entries()){
   const ctx=await browser.newContext({viewport:{width,height:850},hasTouch:i===1});
   const page=await ctx.newPage();
   await ctx.addInitScript(()=>{window.qaPropertyNames=[];const original=CanvasRenderingContext2D.prototype.fillText;CanvasRenderingContext2D.prototype.fillText=function(text,...args){if(this.canvas.width===512&&this.canvas.height===112)window.qaPropertyNames.push(String(text));return original.call(this,text,...args)}});
   async function api(path,method='GET',data){
    const r=await ctx.request.fetch(origin+'/api'+path,{method,data,headers:{Origin:origin,'X-Pulse-Client':'web'}});
    assert(r.ok(),method+' '+path+' HTTP '+r.status());return r.json();
   }
   const username='gcpqaProp'+crypto.randomBytes(5).toString('hex'),password=crypto.randomBytes(24).toString('base64url')+'!aA1';
   const account=await api('/auth/register','POST',{username,email:username+'@example.test',password,confirm_password:password,adult:true,accepted_terms:true,accepted_privacy:true});
   await api('/onboarding','POST',{city:'london',avatar:{},privacy:'City Mode',location_consent:false,analytics_consent:false,interests:[]});
   await api('/world/enter','POST',{city:'london'});
   const balance=(await api('/wallet')).xp;assert(balance>=12,'Acceptance accounts require legitimately earned XP');
   users.push({api,page,balance,id:account.user.id,username,ctx});
  }
  const [a,b]=users;
  for(const city of ['london','milton-keynes']){
   if(city!=='london'){
    await a.api('/growth/worlds/'+city+'/starter','POST',{confirmed:true});
   }
   await a.api('/world/enter','POST',{city});
   const snapshot=await a.api('/world/'+city);
   const candidates=(await a.api('/properties/city/'+city)).items;
   const p=candidates.find(x=>!x.owned&&x.enabled&&x.category!=='venue'&&snapshot.properties.some(n=>n.id===x.id))||
           candidates.find(x=>!x.owned&&x.enabled&&x.category!=='venue');
   assert(p,city+' must expose mapped inventory');ids.push(p.id);originalQuotes[p.id]={price:p.price,enabled:p.enabled};
  }
  quote('prepare');prepared=true;
  for(const [i,city] of ['london','milton-keynes'].entries()){
   const key=ids[i],label='QA '+city+' '+process.env.GITHUB_RUN_ID;
   const item=await a.api('/properties/detail/'+encodeURIComponent(key));assert.equal(item.price,5);
   let req={amount:item.price,request_key:crypto.randomUUID()},result;
   if(city==='london'){
    await a.api('/world/enter','POST',{city});await a.page.goto(origin);
    await a.page.getByRole('button',{name:'Account settings',exact:true}).click();
    await a.page.getByRole('button',{name:'🏡 My Properties',exact:true}).click();
    const sheet=a.page.getByRole('dialog',{name:'My Properties'});
    await sheet.locator('[data-property-id="'+key+'"]').click();
    await sheet.getByRole('button',{name:/MAKE IT MINE/}).click();
    const response=a.page.waitForResponse(r=>decodeURIComponent(new URL(r.url()).pathname)==='/api/properties/'+key+'/claim'&&r.request().method()==='POST');
    await sheet.getByRole('button',{name:'Confirm purchase'}).click();
    const done=await response;assert(done.ok());result=await done.json();req=done.request().postDataJSON();
    await sheet.getByText(/Congratulations! You’re now a property owner!/).waitFor();
    await a.page.screenshot({path:out+'/property-desktop-claim.png'});
   }else{
    result=await a.api('/properties/'+key+'/claim','POST',req);
   }
   const replay=await a.api('/properties/'+key+'/claim','POST',req);
   assert.equal(result.receipt,replay.receipt);
   await a.api('/properties/'+key+'/studio','PATCH',{name:label,board:'forest',colors:{wall:'#234e51'},access:'private'});
   assert((await a.api('/properties/portfolio')).some(p=>p.id===key&&p.name===label));
   evidence.cities[city]={id:key,receipt:result.receipt,price:item.price,name:label};
  }
  assert.equal((await a.api('/wallet')).xp,a.balance-10);
  await a.api('/world/enter','POST',{city:'london'});
  await b.page.goto(origin);
  await b.page.getByRole('button',{name:'Account settings',exact:true}).click();
  await b.page.getByRole('button',{name:'🏡 My Properties',exact:true}).click();
  const panel=b.page.getByRole('dialog',{name:'My Properties'});
  const name=evidence.cities.london.name;
  await panel.getByRole('button',{name:new RegExp(name)}).click();
  await panel.getByLabel('Your XP offer').fill('12');await panel.getByRole('button',{name:'Make an XP offer'}).click();
  await panel.getByText('Offer delivered to the owner.').waitFor();
  const offer=(await a.api('/properties/offers')).find(o=>o.property_id===ids[0]&&o.state==='pending'&&o.amount===12);assert(offer);
  await a.api('/properties/offers/'+offer.id,'POST',{action:'accept',expected_amount:12});
  assert.equal((await b.api('/wallet')).xp,b.balance-12);assert.equal((await a.api('/wallet')).xp,a.balance+2);
  assert((await b.api('/properties/portfolio')).some(p=>p.id===ids[0]&&p.mine));
  await b.page.reload();await b.page.getByRole('button',{name:'Account settings',exact:true}).click();await b.page.getByRole('button',{name:'🏡 My Properties',exact:true}).click();
  await panel.getByRole('button',{name:'Portfolio',exact:true}).click();await panel.locator('button[class*="card"]').first().click();await panel.getByText('Property Studio',{exact:true}).waitFor();
  await b.page.screenshot({path:out+'/property-mobile-owner.png'});
  // Transfer deliberately resets the seller's customization. The new owner
  // publishes their own name before verifying the world-rendered nameboard.
  const newOwnerName=name+' New Owner';await panel.getByLabel('Name my property').fill(newOwnerName);
  await panel.getByRole('button',{name:'Save and publish'}).click();await panel.getByText('Property published.').waitFor();
  assert.equal((await b.api('/properties/detail/'+encodeURIComponent(ids[0]))).name,newOwnerName);
  await panel.getByRole('button',{name:'Visit property',exact:true}).click();await panel.waitFor({state:'hidden'});
  await b.page.locator('.world-canvas[data-ready=true] canvas').first().waitFor({timeout:60000});
  await b.page.waitForFunction(name=>window.qaPropertyNames.includes(name),newOwnerName);
  await b.page.screenshot({path:out+'/property-nameboard-world.png'});evidence.nameboard_texture=true;
  const surface=await b.page.locator('.world-canvas canvas').first().boundingBox();assert(surface);
  for(let angle=0;angle<4;angle++){
   await b.page.mouse.move(surface.x+surface.width*.25,surface.y+surface.height*.45);await b.page.mouse.down();
   await b.page.mouse.move(surface.x+surface.width*.5,surface.y+surface.height*.45,{steps:20});await b.page.mouse.up();
   await b.page.waitForTimeout(300);await b.page.screenshot({path:out+'/property-nameboard-angle-'+angle+'.png'});
  }
  evidence.resale={xp:12,buyer_delta:-12,seller_delta:12};evidence.two_city_portfolio=true;
  await require('./seating-acceptance.cjs')({origin,out,host:{...a,api:(path,data)=>a.api(path,data?'POST':'GET',data)},guest:{...b,api:(path,data)=>b.api(path,data?'POST':'GET',data)},record:check=>{evidence.seating_checks.push(check);console.log('PASS',check)}});
 }finally{
  try{if(prepared){quote('restore');evidence.quote_restoration=[];for(const key of ids){const after=await users[0].api('/properties/detail/'+encodeURIComponent(key));assert.deepEqual({price:after.price,enabled:after.enabled},originalQuotes[key],'Original quote restored for '+key);evidence.quote_restoration.push({id:key,before:originalQuotes[key],after:{price:after.price,enabled:after.enabled}});}evidence.quotes_restored=true;}}
  finally{fs.writeFileSync(out+'/property-acceptance.json',JSON.stringify(evidence,null,2));await browser.close()}
 }
}
main().catch(e=>{console.error(e.message);process.exitCode=1});
