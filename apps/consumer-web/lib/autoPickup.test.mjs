import {test} from 'node:test';
import assert from 'node:assert/strict';
import {PickupGate} from './autoPickup.ts';
test('pickup range is two metres and selects nearest fruit or gem',()=>{
 const gate=new PickupGate();const items=[{id:'far',kind:'fruit',x:2.01,z:0},{id:'edge',kind:'fruit',x:2,z:0},{id:'gem',kind:'gem',x:1,z:0},{id:'other',kind:'treasure',x:0,z:0}];
 assert.equal(gate.nearest({x:0,z:0},items).id,'gem');
 assert.equal(gate.nearest({x:0,z:0},items.slice(0,2)).id,'edge');
 assert.equal(gate.nearest({x:0,z:0},items.slice(0,1)),undefined);
});
test('pending requests and confirmed stale snapshots cannot repeat',()=>{
 const gate=new PickupGate();const item={id:'apple',kind:'fruit',x:0,z:0};
 assert.equal(gate.begin(item.id,0),true);
 for(let i=0;i<100;i++){assert.equal(gate.begin(item.id,i),false);assert.equal(gate.nearest(item,[item],i),undefined)}
 gate.finish(item.id,true,100);assert.equal(gate.nearest(item,[item],9000),undefined);
 assert.equal(gate.begin(item.id,9000),false);
});
test('failed pickup remains retryable after cooldown without frame spam',()=>{
 const gate=new PickupGate();const item={id:'orange',kind:'fruit',x:0,z:0};
 gate.begin(item.id,0);gate.finish(item.id,false,100);
 assert.equal(gate.nearest(item,[item],8099),undefined);
 assert.equal(gate.nearest(item,[item],8100).id,item.id);
 assert.equal(gate.begin(item.id,8100),true);
});
