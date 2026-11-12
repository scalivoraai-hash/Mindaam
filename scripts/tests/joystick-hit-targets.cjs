// Render the shipped CSS with the same canvas/portal stacking as World.tsx.
// No accounts, app APIs, synthetic movement acknowledgement or provider calls.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require(process.env.QA_NODE_MODULES+'/playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.QA_CHROMIUM?{executablePath:process.env.QA_CHROMIUM}:{})});
 try{
  const css=['globals.css','premium.css'].map(file=>fs.readFileSync('apps/consumer-web/app/'+file,'utf8')).join('\n');
  for(const width of [320,360,390,430,768]){
   const page=await browser.newPage({viewport:{width,height:844}});
   await page.setContent('<style>'+css+'</style><main class="world-playing"><div class="world-canvas world-upgrade"><div class="mobile-joystick"><span>✥</span></div></div><div class="city-action-tools"><button>Enter Waterstones · 0 inside</button></div></main>');
   const result=await page.evaluate(()=>{
    const stick=document.querySelector('.mobile-joystick'),r=stick.getBoundingClientRect(),action=document.querySelector('.city-action-tools button'),a=action.getBoundingClientRect();
    const misses=[];
    for(let i=0;i<32;i++){
     const angle=i*Math.PI/16,x=r.x+r.width*(.5+.36*Math.cos(angle)),y=r.y+r.height*(.5+.36*Math.sin(angle));
     if(!stick.contains(document.elementFromPoint(x,y)))misses.push({x,y});
    }
    return {misses,actionAccessible:action===document.elementFromPoint(a.x+a.width/2,a.y+a.height/2),overflow:document.documentElement.scrollWidth>innerWidth};
   });
   assert.deepEqual(result.misses,[],width+' joystick must receive touch in every direction');
   assert.equal(result.actionAccessible,true,width+' building entry remains accessible');
   assert.equal(result.overflow,false,width+' no horizontal overflow');
   await page.close();
  }
  console.log('Joystick and building-entry hit targets passed at five mobile/tablet widths');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
