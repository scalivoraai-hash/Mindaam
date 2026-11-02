import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from 'three';
import {cinematicCharacterPose} from './CinematicCharacterPose.ts';

function fixture(){
 const player=new T.Group(),model=new T.Group();player.add(model);player.position.set(87,2,-41);player.rotation.y=.4;
 for(const name of ['head','spine01',...['upperarm01','lowerarm01','upperleg01','lowerleg01'].flatMap(n=>[n+'L',n+'R'])]){
  const bone=new T.Bone();bone.name=name;model.add(bone);
 }
 return {player,model,pose:cinematicCharacterPose(model,true)};
}
test('rig animation, emotes and transport poses never change authoritative player transform',()=>{
 const {player,model,pose}=fixture(),before=player.matrix.compose(player.position,player.quaternion,player.scale).toArray();
 for(let i=0;i<180;i++)pose.animate(i/60,12,'run',i>90?'wave':'',true);
 const leg=model.getObjectByName('upperleg01L');assert(Math.abs(leg.rotation.x)>.01);
 pose.sit();pose.cycle(4,10);pose.swim(5);
 assert.deepEqual(player.matrix.compose(player.position,player.quaternion,player.scale).toArray(),before);
});
test('stopping after a transport pose returns limbs and model to standing without a one-frame snap',()=>{
 const {model,pose}=fixture();pose.sit();const before=model.position.y;
 pose.animate(0,0,'walk');assert(model.position.y>before&&model.position.y<-.1);
 for(let i=1;i<=180;i++)pose.animate(i/60,0,'walk');
 assert(Math.abs(model.position.y)<.02);
 assert(Math.abs(model.getObjectByName('upperleg01L').rotation.x)<.001);
 assert(Math.abs(model.getObjectByName('lowerleg01L').rotation.x)<.001);
});
test('unknown rigs fail closed rather than yielding a partially animated character',()=>{
 assert.throws(()=>cinematicCharacterPose(new T.Group()),/Unsupported cinematic character rig/);
});
