import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from 'three';
import {propertyBoards,propertyFrontages} from './PropertyBoards.ts';

const building={id:'1',tags:{building:'yes'},points:[[0,0],[10,0],[10,10],[0,10],[0,0]]};
const road={id:'road',tags:{highway:'residential'},points:[[-20,-3],[20,-3]]};
const property={id:'city:1',name:'Sera Villa',x:5,z:10,owned:true,color:'forest',colors:{wall:'#234e51'}};

test('a rear inventory anchor uses the street facade without changing the stored property or map',()=>{
 const original=JSON.stringify([building,road,property]);
 const anchor=propertyFrontages([building,road],'city')(property);
 assert.ok(anchor.z<0);assert.equal(anchor.id,'1');assert.ok(anchor.width<=8);
 assert.equal(JSON.stringify([building,road,property]),original);
 assert.equal(propertyFrontages([building,road],'other')(property),undefined);
});

test('the ownership board is visible before the wall from the street and above the original sign',()=>{
 const previous=globalThis.document;
 globalThis.document={createElement:()=>({width:0,height:0,getContext:()=>({fillRect(){},fillText(){}})})};
 try{
  const scene=new T.Scene(),boards=propertyBoards(scene,()=>{},[building,road],'city');
  boards.update([property]);const board=boards.objects()[0];
  const wall=new T.Mesh(new T.BoxGeometry(10,6,10),new T.MeshBasicMaterial());wall.position.set(5,3,5);scene.add(wall);scene.updateMatrixWorld(true);
  const hits=new T.Raycaster(new T.Vector3(5,4.2,-8),new T.Vector3(0,0,1)).intersectObjects([board,wall]);
  assert.equal(hits[0].object,board);assert.ok(hits.find(h=>h.object===wall));
  assert.ok(board.position.y-.5>3.1+.72/2);
  boards.dispose();wall.geometry.dispose();wall.material.dispose();
 }finally{globalThis.document=previous;}
});

test('rename replaces the visible texture and leaving the neighbourhood disposes its resources',()=>{
 const previous=globalThis.document,texts=[],tints=[];
 globalThis.document={createElement:()=>({width:0,height:0,getContext:()=>({fillRect(){},fillText(text){texts.push(text)}})})};
 try{
  const scene=new T.Scene(),boards=propertyBoards(scene,(...args)=>tints.push(args),[building,road],'city');
  boards.update([property]);const old=boards.objects()[0];let disposed=0;
  for(const resource of [old.geometry,old.material,old.material.map])resource.addEventListener('dispose',()=>disposed++);
  boards.update([{...property,name:'Sera Residence'}]);assert.equal(disposed,3);assert.ok(texts.includes('Sera Residence'));
  assert.equal(boards.objects().length,1);assert.equal(scene.children.length,1);
  boards.update([]);assert.equal(scene.children.length,0);assert.deepEqual(tints.at(-1),['city:1',{}]);
 }finally{globalThis.document=previous;}
});
