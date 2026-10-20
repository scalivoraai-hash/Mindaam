import {test} from 'node:test';
import assert from 'node:assert/strict';
import {acceptMotion,acceptSnapshot,MotionStall,MotionTransition} from './motionState.ts';
const state={city:'paris',position:{x:4,z:2,zone_id:'world',last_move:10},rental:null};
test('vehicle exit rejects superseded replies across transports without hiding new errors',()=>{
 const gate=new MotionTransition();assert.equal(gate.accepts(1),true);
 assert.equal(gate.begin(4),true);assert.equal(gate.paused,true);assert.equal(gate.begin(4),false);
 assert.equal(gate.accepts(4),false);assert.equal(gate.accepts(2),false);
 gate.finish();assert.equal(gate.paused,false);assert.equal(gate.accepts(4),false);
 assert.equal(gate.accepts(5),true);assert.equal(gate.accepts(undefined),true);
 assert.equal(gate.begin(8),true);gate.finish();assert.equal(gate.accepts(7),false);assert.equal(gate.accepts(9),true);
});
test('authoritative exit position prevents an older snapshot from restoring the rental',()=>{
 const riding={...state,rental:{id:'lease'}};
 const exited=acceptMotion(riding,{position:{...state.position,x:6,last_move:11},rental:null},'paris','world');
 const next=acceptSnapshot(exited,{...riding,players:[{id:'peer'}]});
 assert.equal(next.rental,null);assert.equal(next.position.x,6);assert.equal(next.players.length,1);
});
test('late movement cannot put the player back into a previous city or interior',()=>{
 assert.equal(acceptMotion(state,{position:{x:99,last_move:11}},'london','world'),state);
 assert.equal(acceptMotion(state,{position:{x:99,last_move:11}},'paris','building:old'),state);
 assert.equal(acceptMotion(state,{position:{x:99,last_move:9}},'paris','world'),state);
 const next=acceptMotion(state,{position:{...state.position,x:5,last_move:11}},'paris','world');assert.equal(next.position.x,5);
});
test('a late snapshot updates peers without rewinding player motion',()=>{
 const next=acceptSnapshot(state,{...state,players:[{id:'peer'}],position:{...state.position,x:1,last_move:9}});
 assert.equal(next.position.x,4);assert.equal(next.players[0].id,'peer');
 assert.equal(acceptSnapshot(state,{city:'tokyo',position:{x:0,last_move:1}}).city,'tokyo');
 assert.equal(acceptSnapshot(null,state),state);
});
test('recovery is offered only after sustained blocked attempts and clears on release',()=>{
 const stall=new MotionStall();assert.equal(stall.update(true,100),false);assert.equal(stall.update(true,2500),false);assert.equal(stall.update(true,2600),true);
 assert.equal(stall.update(false,2700),false);assert.equal(stall.update(true,2900),false);
});
test('a delayed passenger snapshot cannot rewind a moving bus at the same motion revision',()=>{
 const aboard={city:'london',server_time:100,position:{x:8,z:4,last_move:90,zone_id:'bus:1'}};
 assert.equal(acceptSnapshot(aboard,{...aboard,server_time:99,position:{...aboard.position,x:1}}),aboard);
});
