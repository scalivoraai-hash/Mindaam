import * as T from 'three';
import {mergeGeometries} from 'three/examples/jsm/utils/BufferGeometryUtils.js';

/** Keep spatial culling while packing solid colours into vertex colours. */
export function batchStaticCity(district:T.Group){
  const batches=new Map<string,{material:T.Material;geometries:T.BufferGeometry[];originals:T.Mesh[];x:number;z:number}>();
  const shared=new Map<string,T.MeshStandardMaterial>(),chunks:T.Group[]=[];
  district.updateMatrixWorld(true);
  district.traverse(o=>{
    if(!(o instanceof T.Mesh)||Array.isArray(o.material))return;
    const original=o.material;
    let material=original,colour:T.Color|undefined,key=original.uuid;
    if(original instanceof T.MeshStandardMaterial&&!original.transparent&&!original.vertexColors&&!original.map&&!original.normalMap&&!original.roughnessMap&&!original.metalnessMap&&!original.alphaMap&&!original.aoMap&&!original.lightMap&&!original.bumpMap&&!original.displacementMap&&!original.emissiveMap&&original.emissive.getHex()===0){
      key=`solid:${original.roughness}:${original.metalness}:${original.side}:${original.flatShading}:${original.opacity}`;
      colour=original.color;
      if(!shared.has(key)){const m=original.clone();m.color.set('#ffffff');m.vertexColors=true;shared.set(key,m)}
      material=shared.get(key)!;
    }
    const position=new T.Vector3();o.getWorldPosition(position);
    const x=Math.floor(position.x/80)*80+40,z=Math.floor(position.z/80)*80+40;
    let geometry:T.BufferGeometry=o.geometry.clone();
    if(geometry.index){const flat=geometry.toNonIndexed();geometry.dispose();geometry=flat}
    geometry.applyMatrix4(o.matrixWorld);geometry.translate(-x,0,-z);
    if(colour){const colours=new Float32Array(geometry.getAttribute('position').count*3);for(let i=0;i<colours.length;i+=3){colours[i]=colour.r;colours[i+1]=colour.g;colours[i+2]=colour.b}geometry.setAttribute('color',new T.BufferAttribute(colours,3))}
    // Incompatible geometry attributes never enter the same merge operation.
    const layout=Object.entries(geometry.attributes).map(([name,a])=>`${name}:${a.itemSize}:${a.normalized}`).sort().join(',');
    const batchKey=`${x}:${z}:${key}:${layout}`;
    let batch=batches.get(batchKey);if(!batch){batch={material,geometries:[],originals:[],x,z};batches.set(batchKey,batch)}
    batch.geometries.push(geometry);batch.originals.push(o);
  });
  const removals=new Map<T.Object3D,Set<T.Mesh>>();
  for(const batch of batches.values()){
    const geometry=mergeGeometries(batch.geometries,false);
    for(const g of batch.geometries)g.dispose();
    if(!geometry)continue;
    geometry.computeBoundingSphere();
    const chunk=new T.Group();chunk.position.set(batch.x,0,batch.z);
    const m=new T.Mesh(geometry,batch.material);m.castShadow=true;m.receiveShadow=true;chunk.add(m);district.add(chunk);chunks.push(chunk);
    for(const original of batch.originals){
      if(original.parent){let group=removals.get(original.parent);if(!group){group=new Set();removals.set(original.parent,group)}group.add(original)}
      if(!original.geometry.userData.shared)original.geometry.dispose();
    }
  }
  // Object3D.remove scans and splices the same large child array for every mesh.
  // Compact each parent once so world entry leaves time for network/UI work.
  for(const [parent,removed] of removals){
    let kept=0;
    for(const child of parent.children)if(!removed.has(child as T.Mesh))parent.children[kept++]=child;
    parent.children.length=kept;
    for(const child of removed){
      child.parent=null;
      child.dispatchEvent({type:'removed'});
      parent.dispatchEvent({type:'childremoved',child});
    }
  }
  return {chunks,dispose:()=>shared.forEach(m=>m.dispose())};
}
