import test from 'node:test';
import assert from 'node:assert/strict';
import {climateAt,WorldClock,routePose,trafficRoads,nextTrafficRoad,QUALITY} from './worldClimate.ts';
test('five-minute seasons are shared, deterministic and cover all four seasons',()=>{
 const seen=new Set();for(let i=0;i<4;i++){const a=climateAt('london',i*300+1);seen.add(a.season);assert.deepEqual(a,climateAt('london',i*300+1));assert.equal(a.season,climateAt('london',i*300+299).season);}assert.equal(seen.size,4);
});
test('server clock advances without wall-clock dependence and ignores repeated snapshots',()=>{
 const clock=new WorldClock();clock.observe(1000,200);assert.equal(clock.seconds(1200),1001);clock.observe(1000,1200);assert.equal(clock.seconds(2200),1002);clock.observe(1003,3200);assert.equal(clock.seconds(4200),1004);
});
test('traffic follows polyline corners and excludes paths, private roads and short routes',()=>{
 const path=[[0,0],[0,40],[40,40]];assert.deepEqual(routePose(path,50),{x:10,z:40,heading:Math.PI/2,end:false});assert.equal(routePose(path,900).end,true);
 const f=(id,highway,access='yes')=>({id,tags:{highway,access},points:path});assert.deepEqual(trafficRoads([f('a','residential'),f('b','footway'),f('c','primary','private')]).map(r=>r.id),['a']);assert.ok(QUALITY.low.traffic<QUALITY.high.traffic);
});

test('traffic connects endpoints without shortcuts or reversing one-way links',()=>{
 const current={id:'a',tags:{},points:[[0,0],[0,40]],length:40};
 const road=(id,points,tags={})=>({id,points,tags,length:40});
 const wrong=road('blocked',[[30,40],[30,80]]);
 const reversed=road('b',[[40,40],[0,40]]);
 assert.equal(nextTrafficRoad(current,[wrong],0),null);
 assert.deepEqual(nextTrafficRoad(current,[reversed],0).points,[[0,40],[40,40]]);
 assert.equal(nextTrafficRoad(current,[{...reversed,tags:{oneway:'yes'}}],0),null);
});
