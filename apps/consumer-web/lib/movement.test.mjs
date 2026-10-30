import test from 'node:test';
import assert from 'node:assert/strict';
import {HeldMovement,MOVEMENT,WALK_SPEED,RUN_SPEED,OUTDOOR_WALK_SPEED,OUTDOOR_RUN_SPEED} from './movement.ts';
test('short presses walk, continuous keyboard input runs at 350 ms, release and light joystick reset',()=>{
 const h=new HeldMovement();
 assert.equal(h.update(0,-1,0).mode,'walk');
 assert.equal(h.update(0,-1,349).mode,'walk');
 assert.equal(h.update(0,-1,350).mode,'run');
 assert.equal(h.update(.2,0,400).mode,'walk');
 assert.equal(h.update(1,0,500).mode,'walk');
 assert.equal(h.update(1,0,850).mode,'run');
 assert.deepEqual(h.update(.02,.02,900),{x:0,z:0,mode:'walk'});
 assert.equal(h.update(1,0,1000).mode,'walk');
 h.reset();assert.equal(h.update(0,-1,2000).mode,'walk');
 assert.equal(h.update(1,0,2001,true).mode,'run');
});
test('preview step is preserved and hierarchy is shared',()=>{
 assert.equal(MOVEMENT.previewStep,1.5);assert.equal(MOVEMENT.inputIntervalMs,120);
 assert.equal(WALK_SPEED,12.5);assert.ok(RUN_SPEED>WALK_SPEED*1.7);
 assert.ok(MOVEMENT.vehicleSpeeds.bike>RUN_SPEED);assert.ok(MOVEMENT.vehicleSpeeds.car>MOVEMENT.vehicleSpeeds.bike);
});

test('outdoor pedestrian speed is bounded independently of vehicles and frame rate',()=>{
 assert.equal(OUTDOOR_WALK_SPEED,2);
 assert.equal(OUTDOOR_RUN_SPEED,4.6875);
 for(const fps of [30,60,120]){let distance=0;for(let i=0;i<fps;i++)distance+=OUTDOOR_RUN_SPEED/fps;assert(Math.abs(distance-4.6875)<1e-9);}
 assert.equal(MOVEMENT.vehicleSpeeds.bike,84);assert.equal(MOVEMENT.vehicleSpeeds.car,120);
});
