import test from 'node:test';
import assert from 'node:assert/strict';
import {Group} from 'three';
import {detailVehicle} from './WhitehouseVehicles.ts';

test('Whitehouse wheel animation uses displacement and leaves vehicle transforms intact',()=>{
 for(const [kind,count] of [['car',4],['bike',2],['ebike',2],['scooter',4],['motorbike',4],['bus',4]]){
  const model=new Group();
  model.position.set(7,0,3);
  detailVehicle(model,kind);
  const wheels=model.children.filter(part=>part.isLineSegments);
  assert.equal(wheels.length,count);
  model.userData.rollWheels(.5);
  for(const wheel of wheels)assert.equal(wheel.rotation.x,.5/wheel.userData.outerRadius);
  assert.deepEqual(model.position.toArray(),[7,0,3]);
  assert.equal(model.rotation.y,0);
 }
});
