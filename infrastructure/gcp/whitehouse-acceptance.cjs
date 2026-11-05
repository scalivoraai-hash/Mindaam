const assert=require('node:assert/strict');
const {randomUUID}=require('node:crypto');

// Runs inside the existing staging-only browser workflow, on two disposable accounts.
async function verifyWhitehouse(a,b,screenshot){
 const profile=await a.api('/visual-profile/milton-keynes');
 assert.equal(profile.profile,'cinematic-world-v2');
 for(const city of Object.keys(require('../../shared/city-visual-styles.json')))assert.equal((await a.api('/visual-profile/'+city)).profile,'cinematic-world-v2',city);
 for(const user of [a,b]){
  await user.page.locator('.world-canvas[data-ready="true"] canvas').waitFor();
  assert.ok(await user.page.evaluate(()=>performance.getEntriesByType('resource').some(
   entry=>new URL(entry.name).pathname==='/assets/whitehouse/character-5f945139.glb'&&entry.decodedBodySize>0
  )),'Cinematic character downloaded in the actual game');
 }
 await screenshot(a,'whitehouse-world-desktop');
 await a.page.getByRole('button',{name:'Explore Mindaam Cities',exact:true}).click();
 await a.page.getByRole('heading',{name:'Explore Mindaam Cities',exact:true}).waitFor();
 await a.page.locator('.world-search input').fill('London');
 await a.page.locator('.cities-dialog .destination-card').first().waitFor();
 const compact=await a.page.locator('.cities-dialog .destination-card').evaluateAll(es=>es.every(e=>e.offsetHeight<320));assert(compact);
 await screenshot(a,'v2-city-modal');await a.page.getByRole('button',{name:'Close panel',exact:true}).click();

 const request=await a.api('/talk/request',{target_id:b.id,kind:'text'});
 try{
  await b.page.getByRole('button',{name:'Connect',exact:true}).click();
  const panel=user=>user.page.getByRole('region',{name:'Private conversation'});
  for(const [sender,recipient,body] of [[a,b,'Whitehouse staging chat check'],[b,a,'Reply received from the second player']]){
   await panel(sender).getByRole('textbox',{name:'Message',exact:true}).fill(body);
   await panel(sender).getByRole('button',{name:'Send message'}).click();
   await panel(recipient).getByText(body,{exact:true}).waitFor();
  }
  for(let i=0;i<12;i++)await b.api('/talk/'+request.id+'/messages',{id:randomUUID(),body:'Layout sample '+i});
  await panel(a).getByText('Layout sample 11',{exact:true}).waitFor();
  for(const [width,height] of [[1100,760],[390,844],[844,390],[768,1024]]){
   await a.page.setViewportSize({width,height});
   const layout=await panel(a).evaluate(section=>{
    const history=section.querySelector('.floating-messages');
    const footer=section.querySelector('footer'),composer=section.querySelector('form');
    const rect=element=>element.getBoundingClientRect();
    const clear=element=>{
     const bounds=rect(element);
     return section.contains(document.elementFromPoint(bounds.x+bounds.width/2,bounds.y+bounds.height/2));
    };
    return {unobstructed:[composer.querySelector('input'),...footer.querySelectorAll('button,summary')].filter(e=>e.offsetWidth>0).every(clear),history:rect(history).height,toolbar:rect(footer).height,scrollable:history.scrollHeight>history.clientHeight,
     stacked:rect(history).bottom<=rect(composer).top+1&&rect(composer).bottom<=rect(footer).top+1};
   });
   assert.ok(layout.unobstructed&&layout.stacked&&layout.scrollable&&layout.history>layout.toolbar,JSON.stringify(layout));
   await panel(a).getByRole('button',{name:'Voice chat'}).waitFor();
   for(const name of ['LiveFace','Gifts & reactions','Report','Block','End chat'])await panel(a).locator('footer').getByRole('button',{name,exact:true}).waitFor();
   await screenshot(a,'whitehouse-chat-'+width);
  }
 }finally{
  await a.page.setViewportSize({width:1100,height:760});
  await a.api('/talk/'+request.id+'/end',{});
 }
}
module.exports={verifyWhitehouse};
