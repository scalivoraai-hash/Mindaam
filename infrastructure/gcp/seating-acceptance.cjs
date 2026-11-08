/* Shared real keyboard/touch acceptance for local CI and the exact staging image. */
const assert=require('node:assert/strict');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,label,timeout=8000){const end=Date.now()+timeout;while(Date.now()<end){if(await fn())return;await wait(100)}throw Error(label+' timed out')}
module.exports=async function seatingAcceptance({host,guest,origin,out,record}){
 let event;
 for(const u of [host,guest]){
  u.frames=[];
  u.page.on('websocket',ws=>ws.on('framereceived',f=>{try{const v=JSON.parse(String(f.payload));if(['state','motion'].includes(v.type)){u.frames.push(v);if(u.frames.length>150)u.frames.shift()}}catch{}}));
  await u.page.setViewportSize({width:1280,height:900});
 }
 try{
 for(const u of [host,guest]){
  console.log('Entering world',u.username);await u.page.goto(origin);await u.page.locator('.destination-card.is-owned').first().click();
  await u.page.locator('.world-access-modal').getByRole('button',{name:/^Enter /}).click();
  await u.page.locator('.world-canvas[data-ready=true] canvas').first().waitFor({timeout:60000});
 }
 console.log('Creating auditorium');event=await host.api('/events',{title:'Recovery seating acceptance',city:'london',starts_at:Date.now()/1000,venue_mode:'virtual_auditorium',communication_mode:'text',ticket_price:0});
 await host.api('/events/'+event.id+'/state/start',{});await guest.api('/events/'+event.id+'/join',{});await guest.api('/events/'+event.id+'/venue/enter',{});
 for(const u of [host,guest])await u.page.locator('.in-auditorium .world-canvas[data-ready=true] canvas').first().waitFor({timeout:60000});
 const g=guest.page;
 await g.bringToFront();await g.evaluate(()=>document.activeElement?.blur());
 const before=(await guest.api('/world/london')).position;
 await g.keyboard.down('d');
 try{await until(async()=> (await guest.api('/world/london')).position.x>=3.3,'Keyboard approach to chair')}finally{await g.keyboard.up('d')}
 await until(()=>guest.frames.some(f=>f.type==='motion'&&f.position.last_move>before.last_move&&f.position.speed===0),'Keyboard release acknowledgement');
 // Use short real key presses to approach the nearest actual chair after the
 // initial run. Sampling the server avoids assuming a fixed frame/input rate.
 const chairs=Array.from({length:6},(_,row)=>[-7,-5.4,-3.8,3.8,5.4,7].map(x=>({x,z:-3+row*2.1}))).flat();
 for(let attempt=0;attempt<10;attempt++){
  const p=(await guest.api('/world/london')).position;if(p.seated)break;
  const chair=chairs.toSorted((a,b)=>Math.hypot(a.x-p.x,a.z-p.z)-Math.hypot(b.x-p.x,b.z-p.z))[0];
  if(Math.hypot(chair.x-p.x,chair.z-p.z)<=.65)break;
  const dx=chair.x-p.x,dz=chair.z-p.z,key=Math.abs(dx)>Math.abs(dz)?dx>0?'d':'a':dz>0?'s':'w';
  await g.keyboard.down(key);await wait(120);await g.keyboard.up(key);
  await until(()=>guest.frames.some(f=>f.type==='motion'&&f.position.last_move>p.last_move&&f.position.speed===0),'Chair approach release');
 }
 await until(async()=> (await guest.api('/world/london')).position.seated,'Automatic seating after pausing');
 const seated=(await guest.api('/world/london')).position;assert(seated.x>=3.8&&seated.x<=7);assert.equal(seated.z,7.5);
 await until(()=>host.frames.some(f=>f.type==='state'&&f.players.some(p=>p.id===guest.id&&p.seated&&p.seat===seated.seat)),'Remote chair occupancy');
 await until(()=>guest.frames.some(f=>f.type==='state'&&f.position.seated&&f.position.seat===seated.seat),'Own seated snapshot');
 await g.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 await g.screenshot({path:out+'/auditorium-seated.png'});
 const canvas=await g.locator('.world-canvas canvas').first().boundingBox();assert(canvas);
 await g.mouse.move(canvas.x+canvas.width*.25,canvas.y+canvas.height*.4);await g.mouse.down();await g.mouse.move(canvas.x+canvas.width*.75,canvas.y+canvas.height*.4,{steps:20});await g.mouse.up();
 await g.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 await g.screenshot({path:out+'/auditorium-seat-orbit.png'});record('Keyboard approach, neutral acknowledgement, automatic seating and remote occupancy');
 console.log('Refreshing seated guest');await g.reload();
 await g.locator('.destination-card.is-owned').first().click();
 await g.locator('.world-access-modal').getByRole('button',{name:/^Enter /}).click();
 await g.locator('.in-auditorium .world-canvas[data-ready=true] canvas').first().waitFor({timeout:60000});
 assert.equal((await guest.api('/world/london')).position.seat,seated.seat);record('Seated state survives refresh');
 await g.setViewportSize({width:390,height:844});
 const box=await g.locator('.mobile-joystick').boundingBox();assert(box);
 const cdp=await guest.ctx.newCDPSession(g),start=Date.now()/1000;
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:box.x+box.width/2,y:box.y+box.height*.8,id:1}]});
 try{await until(async()=> (await guest.api('/world/london')).position.z>seated.z+1,'Mobile standing and movement')}finally{await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await cdp.detach()}
 await until(()=>guest.frames.some(f=>f.type==='motion'&&f.position.last_move>start&&f.position.speed===0),'Touch release acknowledgement');
 assert.equal((await guest.api('/world/london')).position.seated,false);
 assert.equal(await g.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
 await g.screenshot({path:out+'/auditorium-mobile-standing.png'});record('Touch standing, authoritative displacement, release acknowledgement and mobile layout');

 }finally{if(event)await host.api('/events/'+event.id+'/state/end',{});}
};
