import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from 'three';
import {buildCityEnvironment,buildCityEnvironmentAsync} from './WorldScenery.ts';

// Texture drawing is deterministic; these tests compare the actual scene geometry.
globalThis.document={createElement:()=>({getContext:()=>new Proxy({createLinearGradient:()=>({addColorStop(){}})},{get:(o,k)=>o[k]??(()=>{})})})};
const geo={spawn:[0,0],features:[
 {id:'road',tags:{highway:'residential'},points:[[0,0],[100,0],[100,100]]},
 {id:'park',tags:{leisure:'park'},points:[[5,5],[20,5],[20,20],[5,20],[5,5]]},
 {id:'home',tags:{building:'house'},points:[[25,25],[35,25],[35,35],[25,35],[25,25]]}
]};
function snapshot(root){root.updateMatrixWorld(true);const meshes=[];root.traverse(o=>{if(o instanceof T.Mesh)meshes.push({matrix:o.matrixWorld.toArray(),attributes:Object.fromEntries(Object.entries(o.geometry.attributes).map(([k,a])=>[k,Array.from(a.array)])),index:o.geometry.index?Array.from(o.geometry.index.array):null,colour:o.material.color.toArray(),roughness:o.material.roughness})});return meshes;}
test('incremental scenery preserves roads, parks, buildings and material geometry',async()=>{
 const sync=new T.Group(),asyncRoot=new T.Group();const a=buildCityEnvironment(sync,geo,'milton-keynes');let yields=0;
 const b=await buildCityEnvironmentAsync(asyncRoot,geo,'milton-keynes',()=>false,async()=>{yields++});
 assert.ok(yields>=geo.features.length*2);assert.equal(b.buildings.length,a.buildings.length);assert.deepEqual(snapshot(asyncRoot),snapshot(sync));a.dispose();b.dispose();
});
test('cancelled scenery stops construction and retains explicit resource disposal',async()=>{
 const root=new T.Group();let cancelled=false;
 const result=await buildCityEnvironmentAsync(root,geo,'milton-keynes',()=>cancelled,async()=>{cancelled=true});
 assert.equal(root.children.length,0);assert.equal(result.buildings.length,0);result.dispose();
});
test('default message scheduler completes and releases its ports',async()=>{
 const root=new T.Group();const result=await buildCityEnvironmentAsync(root,geo,'london');assert.equal(result.buildings.length,1);result.dispose();
});
