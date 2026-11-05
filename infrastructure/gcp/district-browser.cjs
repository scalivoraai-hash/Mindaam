/* Authenticated staging only. Browser inputs move the disposable player.
   Position samples come exclusively from the server's realtime frames. */
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const {chromium} = require(process.env.QA_NODE_MODULES + '/playwright');
const {authenticateAndEnter} = require('./browser-flow.cjs');
const routes = require('../../scripts/tests/district-browser-routes.json');
const origin = 'https://mindaam-staging-qfrofqn4pq-nw.a.run.app';
const route = routes.find(item => item.city === process.env.CITY);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const distance = (a,b) => Math.hypot(a[0]-b[0],a[1]-b[1]);
const xy = position => [position.x, position.z];

async function until(check, label, timeout=30000) {
 const end = Date.now()+timeout;
 while(Date.now()<end) { if(await check()) return; await sleep(120); }
 throw Error(label+' timed out');
}

async function drive(page, control, latest, target, stops, runSpeed, navigation, transport) {
 const held = new Set();
 let contact = false;
 const touch = control==='joystick' ? await page.context().newCDPSession(page) : null;
 const stick = touch ? await page.getByLabel('Movement joystick').boundingBox() : null;
 if(touch) assert.ok(stick,'Mobile joystick is visible');
 async function release() {
  if(!held.size&&!contact)return;
  const previousStop=transport.stopSent;
  for(const key of held) await page.keyboard.up(key);
  held.clear();
  if(contact) await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  contact=false;
  await until(()=>transport.stopSent>previousStop&&transport.stopAck>=transport.stopSent,
   'Server acknowledgement of released '+control,8000);
 }
 // The camera is at the application's default outdoor yaw after normal world entry.
 let segmentStart=xy(latest());
 const angle=.7, cos=Math.cos(angle), sin=Math.sin(angle);
 try {
  for(const waypoint of target) {
   let best=Infinity,progress=Date.now();
   while(true) {
    const p=latest(),dx=waypoint[0]-p.x,dz=waypoint[1]-p.z,d=Math.hypot(dx,dz);
    if(d<.70)break;
    if(d<best-.15){best=d;progress=Date.now();}
    if(Date.now()-progress>8000)throw Error('No progress approaching '+JSON.stringify(waypoint)+' from '+JSON.stringify(xy(p))+' blocked='+Boolean(p.blocked));
    // Follow the surveyed line. Aiming only at a distant corner lets an
    // eight-direction keyboard cut across a footprint beside the route.
    const sx=waypoint[0]-segmentStart[0],sz=waypoint[1]-segmentStart[1];
    const length=Math.hypot(sx,sz);
    const along=((p.x-segmentStart[0])*sx+(p.z-segmentStart[1])*sz)/length;
    const fraction=Math.min(1,Math.max(0,along+1.5)/length);
    let ax=segmentStart[0]+fraction*sx-p.x,az=segmentStart[1]+fraction*sz-p.z;
    const aim=Math.hypot(ax,az)||1;
    ax/=aim;az/=aim;
    let x=cos*ax-sin*az,z=sin*ax+cos*az;
    if(!touch){
     // Pick a physical key combination whose next metre is actually open.
     let bestScore=-Infinity;
     for(const [kx,kz] of [[0,-1],[1,-1],[1,0],[1,1],[0,1],[-1,1],[-1,0],[-1,-1]]){
      const norm=Math.hypot(kx,kz),vx=(cos*kx+sin*kz)/norm,vz=(-sin*kx+cos*kz)/norm;
      const next=navigation.step(p.x,p.z,vx,vz);
      const score=(next.x-p.x)*ax+(next.z-p.z)*az-.8*Math.hypot(next.x-p.x-vx,next.z-p.z-vz);
      if(score>bestScore){bestScore=score;x=kx;z=kz;}
     }
    }
    if(touch){
     const strength=Math.min(1,Math.max(.25,d/Math.max(runSpeed*.65,1)));
     await touch.send('Input.dispatchTouchEvent',{type:contact?'touchMove':'touchStart',touchPoints:[{x:stick.x+stick.width*(.5+.36*x*strength),y:stick.y+stick.height*(.5+.36*z*strength),id:1}]});
     contact=true;
    } else {
     const desired=new Set();
     if(Math.abs(x)>.383)desired.add(x>0?'d':'a');
     if(Math.abs(z)>.383)desired.add(z>0?'s':'w');
     for(const k of [...held])if(!desired.has(k)){await page.keyboard.up(k);held.delete(k);}
     for(const k of desired)if(!held.has(k)){await page.keyboard.down(k);held.add(k);}
    }
    // Measure the stopping position after the release acknowledgement.
    // With a held key, the last running frame can precede the stop by metres.
    const duration=Math.min(1200,Math.max(160,1000*(d-.35)/runSpeed));
    await sleep(duration);
    await release();
   }
   stops.push(xy(latest()));segmentStart=waypoint;
  }
 } finally {await release();if(touch)await touch.detach();}
}

async function exercise(browser,control) {
 const mobile=control==='joystick';
 const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1280,height:850},isMobile:mobile,hasTouch:mobile});
 const page=await context.newPage(),states=[];
 const report={city:route.city,control,renderer:'Chromium SwiftShader',release:process.env.RELEASE_SHA,result:'FAIL',blocked:0,acks:0,travelled_m:0,turns:[],milestones:[]};
 const filename='district-evidence/'+route.city+'-'+control;
 const name='gcpqa'+crypto.randomBytes(8).toString('hex');
 let previous,position,collect=false,registered=false;
 const api=async(path,data,method=data===undefined?'GET':'POST')=>{
  const response=await context.request.fetch(origin+'/api'+path,{method,data,headers:{Origin:origin,'X-Pulse-Client':'web'}});
  assert.ok(response.ok(),method+' '+path+' HTTP '+response.status());
  return response.json();
 };
 const u={page,context,states,touch:mobile,api};
 const transport={stopSent:0,stopAck:0,recent:[]};
 const trace=(kind,d)=>{
  transport.recent.push({kind,at_ms:Date.now(),seq:d.seq,type:d.type,x:d.x,z:d.z,
   position:d.position&&{x:d.position.x,z:d.position.z,speed:d.position.speed,blocked:d.position.blocked,last_move:d.position.last_move}});
  if(transport.recent.length>28)transport.recent.shift();
 };
 page.on('websocket',ws=>{
  if(!ws.url().endsWith('/api/realtime'))return;
  ws.on('framesent',frame=>{
   let input;try{input=JSON.parse(frame.payload.toString());}catch{return;}
   if(input.type==='input')trace('sent',input);
   if(input.type==='input'&&input.x===0&&input.z===0)transport.stopSent=input.seq;
  });
  ws.on('framereceived',frame=>{
   let d;try{d=JSON.parse(frame.payload.toString());}catch{return;}
   if(d.type==='motion'||d.type==='motion_error')trace('received',d);
   if(d.type==='state'){states.push({city:d.city});if(states.length>2)states.shift();}
   if(!d.position||d.city!==route.city||d.position.zone_id!=='world'||(position&&d.position.last_move<position.last_move))return;
   position=d.position;
   if(d.type==='motion'&&d.seq===transport.stopSent&&position.speed===0)transport.stopAck=d.seq;
   if(d.type!=='motion'||!collect)return;
   report.acks++;if(position.blocked)report.blocked++;
   const at=xy(position);report.travelled_m+=distance(previous,at);previous=at;
   const net=distance(report.start,at);
   for(const m of [10,50,100,250,500])if(net>=m&&!report.milestones.includes(m))report.milestones.push(m);
  });
 });
 try {
  assert.equal((await api('/health')).environment,'staging');
  await authenticateAndEnter(u,{origin,city:route.city,index:0,identifier:name,name,password:crypto.randomBytes(24).toString('hex')+'!aA',until,setStage:step=>{report.stage=step;if(step==='onboarding-0')registered=true;}});
  registered=true;
  await page.locator('.world-canvas[data-ready="true"][data-visual-profile="cinematic-world-v2"] canvas').waitFor();
  await until(()=>position,'Initial authoritative position');
  report.start=xy(position);previous=report.start;
  assert.ok(distance(report.start,route.start)<1,'District spawn matches the installed route');
  const state=await api('/world/'+route.city);report.speeds=state.movement_config.speeds;
  const {terrainNavigator}=await import('../../apps/consumer-web/lib/terrain.ts');
  const geography=await api('/geography/'+route.city);
  const navigation=terrainNavigator(geography.navigation);
  if(!mobile)await page.getByRole('button',{name:'walk',exact:true}).click();
  await page.screenshot({path:filename+'-spawn.jpg',type:'jpeg',quality:70});
  collect=true;report.stage='outward';
  await drive(page,control,()=>position,route.turns.slice(1),report.turns,report.speeds.run,navigation,transport);
  await sleep(300);
  report.destination=xy((await api('/world/'+route.city)).position);
  report.displacement_m=distance(report.start,report.destination);
  assert.ok(distance(report.destination,route.destination)<2&&report.displacement_m>=250,'Server confirmed the outward route');
  await page.screenshot({path:filename+'-destination.jpg',type:'jpeg',quality:70});
  report.stage='return';
  await drive(page,control,()=>position,route.turns.slice(0,-1).reverse(),report.turns,report.speeds.run,navigation,transport);
  await sleep(300);report.end=xy((await api('/world/'+route.city)).position);
  assert.ok(distance(report.start,report.end)<2&&report.acks>0,'Server confirmed the return');
  report.result='PASS';
 } catch(e){
  report.error=e.message.split('\n')[0];report.transport=transport;
  if(position)report.last_realtime_position=xy(position);
  if(registered&&position)try{
   report.last_http_position=xy((await api('/world/'+route.city)).position);
   await page.screenshot({path:filename+'-failure.jpg',type:'jpeg',quality:70});
  }catch{/* Keep the original failure and last realtime acknowledgement. */}
  throw e;
 }
 finally{
  try {if(registered)await api('/me',undefined,'DELETE');}
  finally{fs.writeFileSync(filename+'.json',JSON.stringify(report,null,2));await context.close();}
 }
}

(async()=>{
 assert.ok(route,'Unknown test district');fs.mkdirSync('district-evidence',{recursive:true});
 const browser=await chromium.launch({args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const failures=[];
 try{for(const control of ['keyboard','joystick'])try{await exercise(browser,control);}catch(e){failures.push(control+' '+e.message.split('\n')[0]);}}
 finally{await browser.close();}
 if(failures.length)throw Error(failures.join(' / '));
})().catch(e=>{console.error(e.message);process.exitCode=1;});
