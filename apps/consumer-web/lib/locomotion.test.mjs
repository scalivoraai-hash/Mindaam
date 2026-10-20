import test from 'node:test';import assert from 'node:assert/strict';
import {Locomotion} from './locomotion.ts';import {RemoteMotion} from './remoteMotion.ts';import {buildingStyle} from './buildingStyle.ts';
test('gait keeps its phase through run transitions and decays into idle',()=>{
 const gait=new Locomotion();for(let i=0;i<120;i++)gait.update(i/60,6,'walk');
 const before=gait.phase;gait.update(2,13,'run');assert.ok(gait.run>0&&gait.run<.3);assert.ok(Math.abs(gait.phase-before)<1);
 for(let i=121;i<240;i++)gait.update(i/60,13,'run');assert.ok(gait.run>.99);
 for(let i=240;i<400;i++)gait.update(i/60,0,'walk');assert.ok(gait.weight<.001&&gait.speed<.001);
});
test('calibrated local and remote gait retain actual running speed at 30, 60 and 120 FPS',()=>{
 for(const fps of [30,60,120]){
  const gait=new Locomotion();let prior=0;
  for(let i=0;i<fps*3;i++){const value=gait.update(i/fps,23.4375,'run',true);assert.ok(value.run>=prior);prior=value.run}
  assert.ok(Math.abs(gait.speed-23.4375)<.001);assert.ok(gait.run>.999);
  for(let i=fps*3;i<fps*5;i++)gait.update(i/fps,0,'walk',true);
  assert.ok(gait.weight<.001);
 }
});
test('remote heading wraps and prediction is bounded when packets stop',()=>{
 const motion=new RemoteMotion();const p={x:0,z:0,sampled_at:1,vehicle:{id:'car',kind:'car',x:0,z:0,heading:Math.PI*2-.02,speed:8}};
 motion.update(p,0,.016);motion.update({...p,sampled_at:1.5,x:4,vehicle:{...p.vehicle,x:4,heading:.02}},.5,.016);
 assert.ok(Math.abs(motion.heading-(Math.PI*2-.02))<.05);
 for(let i=31;i<200;i++)motion.update({...p,sampled_at:1.5,x:4,vehicle:{...p.vehicle,x:4,heading:.02}},i/60,1/60);
 assert.ok(motion.z<=8*.55+.01);assert.ok(motion.speed<.01);
});
test('verified use selects visual families without inventing shops',()=>{
 for(const [building,family] of [['detached','home'],['apartments','apartments'],['retail','shop'],['office','office'],['civic','civic'],['yes','neutral']])assert.equal(buildingStyle({building},'osm:123').family,family);
 assert.equal(buildingStyle({building:'house'},'osm:123').roof,'gabled');
 assert.equal(buildingStyle({building:'apartments',height:'27'},'osm:123').height,27);
 assert.equal(buildingStyle({building:'yes',amenity:'library'},'osm:123').family,'civic');
});

test('full-speed car stays close between existing 500 ms snapshots',()=>{
 const motion=new RemoteMotion();let sample;
 for(let frame=0;frame<240;frame++){
  const time=frame/60;
  if(frame%30===0)sample={x:32*time,z:0,sampled_at:10+time,vehicle:{id:'car',kind:'car',x:32*time,z:0,heading:Math.PI/2,speed:32}};
  motion.update(sample,time,1/60);
  if(frame>60)assert.ok(Math.abs(32*time-motion.x)<2,'vehicle must not trail by several metres');
 }
});
