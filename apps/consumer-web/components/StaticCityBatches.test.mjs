import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from 'three';
import {batchStaticCity} from './StaticCityBatches.ts';

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
