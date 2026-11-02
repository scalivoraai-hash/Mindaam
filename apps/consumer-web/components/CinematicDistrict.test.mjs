import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from 'three';
import {cinematicDistrict} from './CinematicDistrict.ts';
import {buildCityEnvironment} from './WorldScenery.ts';
globalThis.document={createElement:()=>({getContext:()=>new Proxy({createLinearGradient:()=>({addColorStop(){}})},{get:(o,k)=>o[k]??(()=>{})})})};
const features=Array.from({length:40},(_,i)=>({id:String(i),tags:{building:'house'},points:[[i*80,0],[i*80+8,0],[i*80+8,10],[i*80,10],[i*80,0]]}));
function clear(root){root.traverse(o=>{if(o.isMesh&&!o.geometry.userData.shared)o.geometry.dispose()});root.clear()}
test('details index entire dataset, bound tiles and evict when walking across the district',()=>{
 const root=new T.Group(),geo={features},before=JSON.stringify(geo),pilot=cinematicDistrict(root,geo);
 for(let x=0;x<40*80;x+=80){for(let i=0;i<10;i++)pilot.update({x,z:0},'low');assert(pilot.metrics().activeTiles<=9);assert.equal(pilot.metrics().failed,false)}
 assert.equal(pilot.metrics().indexedBuildings,40);assert.equal(JSON.stringify(geo),before);pilot.dispose();pilot.dispose();assert.equal(root.children.length,0);
});
test('cinematic details do not remove base scenery outside Whitehouse',()=>{
 for(const city of ['london','milton-keynes-centre','milton-keynes-willen']){
  const a=new T.Group(),b=new T.Group(),geo={features:features.slice(0,1),spawn:[0,0]};
  const old=buildCityEnvironment(a,geo,city),flag=buildCityEnvironment(b,{...geo,visual_profile:'cinematic-world-v1'},city);
  let ac=0,bc=0;a.traverse(o=>{if(o.isMesh)ac++});b.traverse(o=>{if(o.isMesh)bc++});assert.equal(ac,bc);old.dispose();flag.dispose();clear(a);clear(b);
 }
});
test('Whitehouse uses one entrance system while preserving every base footprint',()=>{
 const a=new T.Group(),b=new T.Group(),geo={features:features.slice(0,1),spawn:[0,0]};
 const old=buildCityEnvironment(a,geo,'milton-keynes'),flag=buildCityEnvironment(b,{...geo,visual_profile:'cinematic-world-v1'},'milton-keynes');
 let ac=0,bc=0;a.traverse(o=>{if(o.isMesh)ac++});b.traverse(o=>{if(o.isMesh)bc++});assert.equal(flag.buildings.length,old.buildings.length);assert(bc<ac);old.dispose();flag.dispose();clear(a);clear(b);
});
