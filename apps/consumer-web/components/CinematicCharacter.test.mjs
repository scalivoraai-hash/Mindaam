import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from 'three';
import {cinematicCharacterFactory} from './CinematicCharacter.ts';

function asset(){
 const root=new T.Group();
 const names=['head','spine01',...['upperarm01','lowerarm01','upperleg01','lowerleg01'].flatMap(n=>[n+'L',n+'R'])];
 const bones=names.map(name=>{const bone=new T.Bone();bone.name=name;root.add(bone);return bone});
 const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute([0,0,0,1,0,0,0,1,0],3));
 geometry.setAttribute('skinIndex',new T.Uint16BufferAttribute(Array(12).fill(0),4));geometry.setAttribute('skinWeight',new T.Float32BufferAttribute([1,0,0,0,1,0,0,0,1,0,0,0],4));
 const texture=new T.Texture(),material=new T.MeshStandardMaterial({map:texture});material.name='skin';
 const mesh=new T.SkinnedMesh(geometry,material);root.add(mesh);mesh.bind(new T.Skeleton(bones));
 return {root,geometry,material,texture};
}
const fallback=()=>{const g=new T.Group();g.userData.setLOD=d=>g.userData.distance=d;return g};
test('clones isolate pose and appearance while sharing mesh and texture storage',()=>{
 const a=asset(),factory=cinematicCharacterFactory(a.root,fallback);
 const first=factory.create({skin:'#915e43'}),second=factory.create({skin:'#d3a782'});
 const skin=root=>{let result;root.traverse(o=>{if(o.isSkinnedMesh)result=o});return result};
 assert.equal(skin(first).geometry,skin(second).geometry);
 assert.notEqual(skin(first).skeleton,skin(second).skeleton);
 assert.notEqual(skin(first).material,skin(second).material);
 assert.equal(skin(first).material.map,skin(second).material.map);
 const before=second.getObjectByName('upperleg01L').rotation.x;
 first.userData.sit();assert.equal(second.getObjectByName('upperleg01L').rotation.x,before);
 first.userData.dispose();second.userData.animate(1,3,'walk');assert.equal(factory.metrics().instances,1);
 factory.dispose();
});
test('near/far switching is bounded and lease cleanup disposes shared resources once',()=>{
 const a=asset(),counts={geometry:0,material:0,texture:0};
 for(const key of Object.keys(counts))a[key].addEventListener('dispose',()=>counts[key]++);
 const factory=cinematicCharacterFactory(a.root,fallback),person=factory.create();
 for(let i=0;i<50;i++){person.userData.setLOD(60);person.userData.setLOD(10)}
 assert.equal(person.children.length,2);assert.equal(person.children[0].visible,true);assert.equal(person.children[1].visible,false);
 person.userData.dispose();person.userData.dispose();assert.deepEqual(counts,{geometry:0,material:0,texture:0});
 factory.dispose();factory.dispose();assert.deepEqual(counts,{geometry:1,material:1,texture:1});
 assert.throws(()=>factory.create(),/lease is closed/);
});
test('unsupported existing hair styles retain the existing avatar rather than silently changing appearance',()=>{
 const a=asset();let received;
 const factory=cinematicCharacterFactory(a.root,(appearance,calibrated)=>{received={appearance,calibrated};return fallback()});
 factory.create({style:'long',color:'#abcdef'},true);
 assert.deepEqual(received,{appearance:{style:'long',color:'#abcdef'},calibrated:true});
 assert.equal(factory.metrics().instances,0);factory.dispose();
});

test('far avatars keep existing locomotion, riding and expression hooks',()=>{
 const a=asset(),calls=[];let far;
 const factory=cinematicCharacterFactory(a.root,()=>{far=fallback();for(const method of ['animate','sit','cycle','swim'])far.userData[method]=(...args)=>calls.push([method,...args]);return far});
 const person=factory.create();person.userData.setLOD(60);person.userData.emote='wave';person.userData.speaking=true;
 person.userData.animate(2,3,'walk');person.userData.sit();person.userData.cycle(3,4);person.userData.swim(4);
 assert.deepEqual(calls,[['animate',2,3,'walk'],['sit'],['cycle',3,4],['swim',4]]);
 assert.equal(far.userData.emote,'wave');assert.equal(far.userData.speaking,true);factory.dispose();
});
