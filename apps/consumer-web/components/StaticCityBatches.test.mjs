import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from 'three';
import {batchStaticCity,batchStaticCityAsync} from './StaticCityBatches.ts';

test('static batching reduces coloured draw calls without moving geometry or mixing tiles',()=>{
  const root=new T.Group();
  for(const [x,colour] of [[4,'#448866'],[10,'#aabbcc'],[190,'#448866']]){const mesh=new T.Mesh(new T.BoxGeometry(2,2,2),new T.MeshStandardMaterial({color:colour,roughness:.74}));mesh.position.set(x,2,10);root.add(mesh)}
  root.updateMatrixWorld(true);const before=new T.Box3().setFromObject(root),result=batchStaticCity(root);
  assert.equal(result.chunks.length,2);
  const after=new T.Box3().setFromObject(root);assert.deepEqual(after.min.toArray(),before.min.toArray());assert.deepEqual(after.max.toArray(),before.max.toArray());
  const mesh=result.chunks[0].children[0];assert.equal(mesh.material.vertexColors,true);
  const colours=mesh.geometry.getAttribute('color'),expected=new T.Color('#448866');assert.ok(Math.abs(colours.getX(0)-expected.r)<1e-7);
  assert.equal(mesh.geometry.getAttribute('position').count,72);
  result.dispose();
});
test('textured and differently structured geometry remains present after batching',()=>{
  const root=new T.Group(),material=new T.MeshStandardMaterial({map:new T.Texture()});
  const a=new T.Mesh(new T.BoxGeometry(),material),b=new T.Mesh(new T.BoxGeometry(),material);b.geometry.deleteAttribute('uv');root.add(a,b);
  const result=batchStaticCity(root);assert.equal(result.chunks.length,2);assert.ok(result.chunks.every(g=>g.children[0].material===material));
});

test('large sibling batches detach once, preserve retained order and emit cleanup events',()=>{
  const root=new T.Group(),before=new T.Object3D(),after=new T.Object3D();
  const geometry=new T.BoxGeometry();geometry.userData.shared=true;
  const material=new T.MeshStandardMaterial(),meshes=[];let removed=0,childRemoved=0,disposed=0;
  geometry.addEventListener('dispose',()=>disposed++);
  root.add(before);
  for(let i=0;i<2048;i++){
    const mesh=new T.Mesh(geometry,material);mesh.position.x=i%20;
    mesh.addEventListener('removed',()=>{assert.equal(mesh.parent,null);removed++});
    root.add(mesh);meshes.push(mesh);
  }
  root.add(after);root.addEventListener('childremoved',event=>{assert.ok(meshes.includes(event.child));childRemoved++});
  // Guard the actual quadratic operations, without a machine-dependent deadline.
  root.children.indexOf=()=>{throw Error('Repeated sibling search')};
  root.children.splice=()=>{throw Error('Repeated sibling splice')};
  const result=batchStaticCity(root);
  assert.equal(root.children[0],before);assert.equal(root.children[1],after);
  assert.equal(root.children.length,2+result.chunks.length);
  assert.equal(removed,2048);assert.equal(childRemoved,2048);assert.equal(disposed,0);
  assert.ok(meshes.every(mesh=>mesh.parent===null));
  result.dispose();
});

test('incremental batching yields before completion and preserves the synchronous geometry',async()=>{
  const make=()=>{const root=new T.Group(),material=new T.MeshStandardMaterial({color:'#448866'});for(let i=0;i<512;i++){const mesh=new T.Mesh(new T.BoxGeometry(),material);mesh.position.set(i%30,i%3,Math.floor(i/30));root.add(mesh)}return root};
  const sync=make(),incremental=make(),expected=batchStaticCity(sync);let turns=0,complete=false;
  const pending=batchStaticCityAsync(incremental,async()=>{assert.equal(complete,false);turns++;await new Promise(resolve=>setTimeout(resolve,0))});
  assert.equal(turns,1);const actual=await pending;complete=true;
  assert.ok(turns>=5,'large batches return control between bounded groups');
  assert.equal(actual.chunks.length,expected.chunks.length);
  for(let i=0;i<actual.chunks.length;i++){
    assert.deepEqual(actual.chunks[i].position.toArray(),expected.chunks[i].position.toArray());
    for(const key of ['position','normal','uv','color'])assert.deepEqual(actual.chunks[i].children[0].geometry.getAttribute(key).array,expected.chunks[i].children[0].geometry.getAttribute(key).array);
  }
  actual.dispose();expected.dispose();
});

test('default browser task yielding completes and closes its message ports',async()=>{
  const root=new T.Group();root.add(new T.Mesh(new T.BoxGeometry(),new T.MeshStandardMaterial()));
  const result=await batchStaticCityAsync(root);assert.equal(result.chunks.length,1);result.dispose();
});

test('cancelled scene setup stops at its next yield and leaves originals for scene cleanup',async()=>{
  const root=new T.Group(),geometry=new T.BoxGeometry(),material=new T.MeshStandardMaterial();let cancelled=false,turns=0,disposed=0;
  geometry.addEventListener('dispose',()=>disposed++);
  for(let i=0;i<512;i++)root.add(new T.Mesh(geometry,material));
  const result=await batchStaticCityAsync(root,async()=>{cancelled=true;turns++},()=>cancelled);
  assert.ok(turns<=2);assert.equal(result.chunks.length,0);assert.equal(root.children.length,512);assert.equal(disposed,0);
  result.dispose();geometry.dispose();material.dispose();
});
