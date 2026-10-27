/* Shared bounded actionability checks; never inspect input values. */
async function waitUI(page,timeout=60000){
 await page.bringToFront();
 // The current app no longer guarantees a persistent main.app wrapper. Treat the UI
 // as ready when any real interactive application surface is visible.
 await page.locator('.splash').waitFor({state:'hidden',timeout}).catch(()=>{});
 const surfaces=page.locator('.auth-card, .onboarding, .welcome-home, .world-playing');
 await surfaces.first().waitFor({state:'visible',timeout});
}
async function inspectControl(locator){
 const count=await locator.count(),elements=[];
 for(let i=0;i<Math.min(count,10);i++){
  const el=locator.nth(i);
  try{elements.push({...await el.evaluate(e=>{
   const r=e.getBoundingClientRect(),x=Math.max(0,Math.min(innerWidth-1,r.x+r.width/2)),y=Math.max(0,Math.min(innerHeight-1,r.y+r.height/2));
   const top=document.elementFromPoint(x,y),describe=n=>n?{tag:n.tagName,role:n.getAttribute('role'),className:typeof n.className==='string'?n.className:''}:null;
   return {tag:e.tagName,role:e.getAttribute('role')||(e.tagName==='BUTTON'?'button':e.tagName==='A'&&e.hasAttribute('href')?'link':null),ariaHidden:e.getAttribute('aria-hidden'),inert:!!e.closest('[inert]'),point:{x,y},interceptor:describe(top),receivesPointer:!!top&&(e===top||e.contains(top))};
  }),visible:await el.isVisible(),enabled:await el.isEnabled(),box:await el.boundingBox()})}catch{elements.push({detached:true})}
 }
 return {count,elements};
}
async function act(u,locator,label,method='click',value,timeout=60000){
 u.lastControl={locator,label,method};
 try{
  await waitUI(u.page,timeout);
  const target=locator.filter({visible:true});
  await target.waitFor({state:'visible',timeout});
  await target.scrollIntoViewIfNeeded({timeout});
  const pointer=u.touch?'tap':'click';
  await target[pointer]({trial:true,timeout});
  if(method==='click')await target[pointer]({timeout});
  else if(method==='fill')await target.fill(value,{timeout});
  else if(method==='check')await target.check({timeout});
  else if(method==='selectOption')await target.selectOption(value,{timeout});
  else throw Error('Unsupported UI action');
 }catch(error){u.failedControl={label,method,locator:locator.toString(),...await inspectControl(locator).catch(()=>({inspection_failed:true}))};throw error}
}
function expectedAnonymous(response,u){return response.status()===401&&response.request().method()==='GET'&&new URL(response.url()).pathname==='/api/me'&&u.authExpected===false}
module.exports={waitUI,inspectControl,act,expectedAnonymous};
