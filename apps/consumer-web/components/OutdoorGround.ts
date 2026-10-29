import * as T from 'three';
import {terrainNavigator,type Navigation} from '../lib/terrain';
import type {WorldQuality} from '../lib/worldClimate';

/** One tileable original atlas and a bounded camera-local blade pool. */
export function outdoorGround(scene:T.Scene,terrain:T.Mesh,nav:Navigation,district?:T.Object3D){
 const canvas=document.createElement('canvas');canvas.width=canvas.height=256;const ctx=canvas.getContext('2d')!;
 let seed=9137;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
 ctx.fillStyle='#7f8b68';ctx.fillRect(0,0,256,256);
 for(let i=0;i<14000;i++){const x=random()*256,y=random()*256;ctx.strokeStyle=`rgba(${i%3?42:180},${i%3?65:175},${i%3?28:112},${.12+random()*.23})`;ctx.lineWidth=.6;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+random()*2-1,y-1-random()*5);ctx.stroke();}
 const texture=new T.CanvasTexture(canvas);texture.wrapS=texture.wrapT=T.RepeatWrapping;texture.colorSpace=T.SRGBColorSpace;texture.anisotropy=4;
 const wet={value:0},snow={value:0},autumn={value:0};
 const material=new T.MeshStandardMaterial({map:texture,bumpMap:texture,bumpScale:.035,roughness:.95,color:'#c0c99b'});
 material.userData.outdoorGround=true;
 material.onBeforeCompile=shader=>{
  Object.assign(shader.uniforms,{groundWet:wet,groundSnow:snow,groundAutumn:autumn});
  shader.vertexShader='varying vec3 groundWorld;\n'+shader.vertexShader;
  shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\ngroundWorld=(modelMatrix*vec4(position,1.0)).xyz;');
  shader.fragmentShader='varying vec3 groundWorld;uniform float groundWet;uniform float groundSnow;uniform float groundAutumn;float grassHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}float grassNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(grassHash(i),grassHash(i+vec2(1,0)),f.x),mix(grassHash(i+vec2(0,1)),grassHash(i+vec2(1,1)),f.x),f.y);}\n'+shader.fragmentShader;
  shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`vec2 grassUV=groundWorld.xz*.65;
   vec4 grassTex=texture2D(map,grassUV);diffuseColor*=grassTex;
   float grassPatch=grassNoise(groundWorld.xz*.06)*2.0-1.0;
   diffuseColor.rgb*=.88+grassPatch*.15;
   diffuseColor.rgb=mix(diffuseColor.rgb,diffuseColor.rgb*vec3(1.2,.91,.65),groundAutumn*.45);
   diffuseColor.rgb*=1.0-groundWet*.2;
   diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.8,.86,.9),groundSnow*.85);`);
  shader.fragmentShader=shader.fragmentShader.replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=mix(.95,.65,groundWet);');
  // UV derivatives for bump detail use the same world scale as the colour atlas.
  shader.fragmentShader=shader.fragmentShader.replace('#include <bumpmap_pars_fragment>',T.ShaderChunk.bumpmap_pars_fragment.replaceAll('vBumpMapUv','(groundWorld.xz*.65)'));
 };
 material.customProgramCacheKey=()=> 'mindaam-ground-v1';terrain.material=material;district?.traverse(o=>{if(o instanceof T.Mesh&&o.userData.grassSurface)o.material=material;});
 const bladeGeometry=new T.BufferGeometry();bladeGeometry.setAttribute('position',new T.Float32BufferAttribute([-.035,0,0,.035,0,0,.018,.17,0,0,0,-.035,0,0,.035,0,.14,.018],3));bladeGeometry.computeVertexNormals();
 const bladeMaterial=new T.MeshStandardMaterial({color:'#657f43',roughness:1,side:T.DoubleSide});
 const blades=new T.InstancedMesh(bladeGeometry,bladeMaterial,700);blades.frustumCulled=false;blades.name='Nearby grass blades';scene.add(blades);
 const navigation=terrainNavigator(nav),dummy=new T.Object3D();let cell='',lastQuality='';

 function update(player:T.Vector3,quality:WorldQuality,rain:boolean,season:number,dt:number){
  const k=Math.min(1,dt*.4);wet.value+=((rain?1:0)-wet.value)*k;snow.value+=((season===3?1:0)-snow.value)*k;autumn.value+=((season===2?1:0)-autumn.value)*k;
  bladeMaterial.color.set(season===3?'#d1daca':season===2?'#8a8051':rain?'#4b693a':'#657f43');
  const key=Math.floor(player.x/5)+':'+Math.floor(player.z/5);if(key===cell&&quality===lastQuality)return;cell=key;lastQuality=quality;
  const max=quality==='low'?100:quality==='balanced'?350:700;let used=0;seed=9137+Math.floor(player.x/5)*719+Math.floor(player.z/5)*131;
  for(let i=0;i<max*3&&used<max;i++){const x=Math.floor(player.x/5)*5+(random()-.5)*30,z=Math.floor(player.z/5)*5+(random()-.5)*30;if(!navigation.grass(x,z))continue;
   dummy.position.set(x,.015,z);dummy.rotation.y=random()*Math.PI;dummy.scale.setScalar(.6+random()*.6);dummy.updateMatrix();blades.setMatrixAt(used++,dummy.matrix);
  }
  blades.count=used;blades.instanceMatrix.needsUpdate=true;
 }
 return {update,dispose(){scene.remove(blades);bladeGeometry.dispose();bladeMaterial.dispose();material.dispose();texture.dispose();}};
}
