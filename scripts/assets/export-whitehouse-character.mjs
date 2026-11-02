/* Offline CC0 geometry conversion; no application or remote state is touched. */
import fs from 'node:fs';
import * as T from 'three';
import {GLTFExporter} from 'three/examples/jsm/exporters/GLTFExporter.js';
if(process.argv.length!==4)throw Error('Usage: node export-whitehouse-character.mjs input.json output.glb');
const data=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
if(data.licence!=='CC0-1.0'||data.bones.length>32)throw Error('Unreviewed character input');
const scene=new T.Group();scene.name='Mindaam Whitehouse character development asset';
const bones=data.bones.map(b=>{const bone=new T.Bone();bone.name=b.name;bone.position.fromArray(b.position);return bone});
for(let i=0;i<bones.length;i++){const parent=data.bones[i].parent;if(parent===null)scene.add(bones[i]);else{bones[i].position.sub(new T.Vector3().fromArray(data.bones[parent].position));bones[parent].add(bones[i])}}
scene.updateMatrixWorld(true);const skeleton=new T.Skeleton(bones);skeleton.calculateInverses();
const palette={skin:'#bf855e','casual-clothing':'#5c7d91',pants:'#344458',shoes:'#303a42',hair:'#342a24',eyes:'#f0e8da'};
for(const item of data.meshes){
 const normals=item.positions.map(()=>new T.Vector3());const a=new T.Vector3(),b=new T.Vector3(),c=new T.Vector3();
 for(const face of item.triangles){a.fromArray(item.positions[face[0][0]]);b.fromArray(item.positions[face[1][0]]).sub(a);c.fromArray(item.positions[face[2][0]]).sub(a);const normal=b.cross(c);for(const [v] of face)normals[v].add(normal)}
 normals.forEach(n=>n.normalize());
 const positions=[],uv=[],normal=[],joints=[],weights=[],indices=[],lookup=new Map();
 for(const face of item.triangles)for(const [v,t] of face){const key=v+':'+t;let index=lookup.get(key);if(index===undefined){index=lookup.size;lookup.set(key,index);positions.push(...item.positions[v]);uv.push(...(item.uv[t]||[0,0]));normal.push(...normals[v].toArray());joints.push(...item.joints[v]);weights.push(...item.weights[v])}indices.push(index)}
 const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(positions,3));geometry.setAttribute('normal',new T.Float32BufferAttribute(normal,3));geometry.setAttribute('uv',new T.Float32BufferAttribute(uv,2));geometry.setAttribute('skinIndex',new T.Uint16BufferAttribute(joints,4));geometry.setAttribute('skinWeight',new T.Float32BufferAttribute(weights,4));geometry.setIndex(indices);geometry.computeBoundingSphere();
 const material=new T.MeshStandardMaterial({color:palette[item.name],roughness:item.name==='skin'?.67:.9,side:item.name==='casual-clothing'?T.DoubleSide:T.FrontSide});material.name=item.name;
 const mesh=new T.SkinnedMesh(geometry,material);mesh.name=item.name;mesh.normalizeSkinWeights();scene.add(mesh);mesh.bind(skeleton,new T.Matrix4());
}
// GLTFExporter uses the browser FileReader contract for buffer serialization.
globalThis.FileReader=class {readAsArrayBuffer(blob){blob.arrayBuffer().then(result=>{this.result=result;this.onloadend?.()})}readAsDataURL(blob){blob.arrayBuffer().then(result=>{this.result='data:'+blob.type+';base64,'+Buffer.from(result).toString('base64');this.onloadend?.()})}};
const result=await new GLTFExporter().parseAsync(scene,{binary:true,onlyVisible:false});
fs.writeFileSync(process.argv[3],Buffer.from(result));console.log(JSON.stringify({bones:bones.length,meshes:data.meshes.length,bytes:result.byteLength,status:'unverified asset; requires rigging, appearance, animation and performance acceptance'}));
