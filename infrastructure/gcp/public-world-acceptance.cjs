const assert = require('node:assert/strict');
const fs = require('node:fs');

async function verifyPublicWorld(browser,origin,out){
 const context = await browser.newContext({reducedMotion:'reduce'});
 try {
  const page=await context.newPage();
  await page.addInitScript(()=>{
   window.layoutShift=0;
   new PerformanceObserver(entries=>{
    for(const e of entries.getEntries())if(!e.hadRecentInput)window.layoutShift+=e.value;
   }).observe({type:'layout-shift',buffered:true});
  });
  await page.goto(origin,{waitUntil:'domcontentloaded'});
  const heading=page.getByRole('heading',{name:'A Living World. Together.'});
  await heading.waitFor();
  const measurements=[];
  for(const width of [320,360,375,390,430,600,768,820,1024,1280,1440,1920,844]){
   const height=width===844?390:850;
   await page.setViewportSize({width,height});
   const bounds=await page.evaluate(()=>{
    const a=document.querySelector('.arrival-copy').getBoundingClientRect();
    const b=document.querySelector('.auth-card').getBoundingClientRect();
    return {overflow:document.querySelector('.auth-shell').scrollWidth>innerWidth,
     overlap:a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top};
   });
   assert.deepEqual(bounds,{overflow:false,overlap:false},'Public layout '+width);
   measurements.push({width,height,...bounds});
   if([320,390,844,1440].includes(width))await page.screenshot({path:out+'/public-world-'+width+'.jpg'});
  }
  const auth=page.getByRole('link',{name:'Enter Mindaam',exact:true});
  await auth.click();
  assert.equal(new URL(page.url()).hash,'#enter-mindaam');
  await page.getByRole('button',{name:'New here? Create an account'}).click();
  await page.getByLabel('Confirm password',{exact:true}).waitFor();
  for(const city of ['London','Dubai','New York','Kochi']){
   await page.getByRole('button',{name:new RegExp('^'+city)}).click();
   await page.getByRole('img',{name:city+' mapped street illustration'}).waitFor();
  }
  assert.equal(await page.locator('.arrival-sky').evaluate(e=>getComputedStyle(e).animationName),'none');
  const metrics=await page.evaluate(()=>({
   paint:performance.getEntriesByType('paint').map(e=>({name:e.name,ms:e.startTime})),
   layoutShift:window.layoutShift,webglCanvases:document.querySelectorAll('canvas').length,
   eagerGeography:performance.getEntriesByType('resource').some(e=>e.name.includes('/api/geography/'))
  }));
  assert.equal(metrics.eagerGeography,false);assert.equal(metrics.webglCanvases,0);
  await page.getByRole('link',{name:/Preview the World/}).first().click();
  await page.waitForURL('**/explore');
  fs.writeFileSync(out+'/public-world.json',JSON.stringify({measurements,metrics},null,2));
 } finally {await context.close();}
}
module.exports={verifyPublicWorld};
