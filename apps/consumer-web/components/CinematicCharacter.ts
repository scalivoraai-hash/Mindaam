import * as T from 'three';
import {avatarWardrobe} from './AvatarWardrobe.ts';
import {clone} from 'three/examples/jsm/utils/SkeletonUtils.js';
import {cinematicCharacterPose} from './CinematicCharacterPose.ts';
import type {Appearance} from './WorldAssets.ts';

/** Owns one loaded template and all clones. Caller must dispose on city exit.
 * Used only by the optional Whitehouse staging visual profile.
 */
export function cinematicCharacterFactory(template:T.Object3D,fallback:(appearance:Appearance,calibrated:boolean)=>T.Group){
 const geometries=new Set<T.BufferGeometry>(),materials=new Set<T.Material>(),textures=new Set<T.Texture>();
 template.traverse(object=>{
  if(!(object instanceof T.Mesh))return;
  geometries.add(object.geometry);object.geometry.userData.shared=true;
  for(const material of Array.isArray(object.material)?object.material:[object.material]){
   materials.add(material);
   if(material instanceof T.MeshStandardMaterial&&material.map)textures.add(material.map);
  }
 });
 let disposed=false;
 const instances=new Set<()=>void>();
 return {
  create(appearance:Appearance={},calibrated=false){
   if(disposed)throw Error('Character asset lease is closed');
   // Preserve unsupported hair styles until their actual assets are admitted.
   if(appearance.version!=='2'&&appearance.style&&appearance.style!=='short')return fallback(appearance,calibrated);
   const root=new T.Group(),model=clone(template);root.add(model);
   // Validate before allocating per-instance materials. A rejected rig owns no GPU resources.
   const wardrobe=appearance.version==='2'?avatarWardrobe(model,appearance):null;
   const pose=cinematicCharacterPose(model,calibrated);
   const ownedMaterials=new Set<T.Material>(),skeletons=new Set<T.Skeleton>(),ownedGeometry=new Set<T.BufferGeometry>();
   const colors:Record<string,string|undefined>={skin:appearance.skin,hair:appearance.hair,'casual-clothing':appearance.color,pants:appearance.pants};
   model.traverse(object=>{
    if(!(object instanceof T.Mesh))return;
    object.castShadow=true;object.receiveShadow=true;
    if(appearance.version==='2'&&object.name==='hair'&&['hijab','turban','kufi','thoppi','beanie'].includes(appearance.headwear||''))object.visible=false;
    // The source rig has no concealed torso/leg skin: retain its skinned surfaces.
    if(appearance.version==='2'&&['mundu','lungi','saree','half-saree','abaya','frock'].includes(appearance.bottom||'')&&object.name==='pants')object.visible=false;
    const copy=(source:T.Material)=>{
     const material=source.clone();ownedMaterials.add(material);
     if(material instanceof T.MeshStandardMaterial&&colors[material.name]){
      material.color.set(colors[material.name]!);
      if(appearance.version==='2'&&['casual-clothing','pants'].includes(material.name)){
       material.map=null;material.roughness=.85;
       if(['abaya','frock','saree','half-saree','kurti-pants'].includes(appearance.bottom||'')&&object.name==='casual-clothing')material.color.set(appearance.bottom==='abaya'?appearance.pants!:appearance.color!);
      }
     }
     return material;
    };
    object.material=Array.isArray(object.material)?object.material.map(copy):copy(object.material);
    if(object instanceof T.SkinnedMesh)skeletons.add(object.skeleton);
    const shortSleeve=appearance.version==='2'&&object.name==='casual-clothing'&&['t-shirt','beach-shirt','sports-tee','striped-tee','waistcoat'].includes(appearance.top||'')&&!['abaya'].includes(appearance.bottom||'');
    const shorts=appearance.version==='2'&&object.name==='pants'&&appearance.bottom==='shorts';
    if(shortSleeve||shorts){
     const clothing=object.material as T.MeshStandardMaterial,skin=new T.Color(appearance.skin||'#bf855e');
     clothing.onBeforeCompile=shader=>{
      shader.uniforms.exposedSkin={value:skin};
      shader.vertexShader='varying vec3 avatarRest;\n'+shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\navatarRest=position;');
      shader.fragmentShader='varying vec3 avatarRest;uniform vec3 exposedSkin;\n'+shader.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\nif('+ (shorts?'avatarRest.y<.83':'abs(avatarRest.x)>.43') +')diffuseColor.rgb=exposedSkin;');
     };
     clothing.customProgramCacheKey=()=>shorts?'avatar-shorts-v2':'avatar-short-sleeves-v2';
     if(shorts){const g=object.geometry.clone();ownedGeometry.add(g);object.geometry=g;delete g.userData.shared;const p=g.getAttribute('position');for(let i=0;i<p.count;i++){const y=p.getY(i),x=p.getX(i);if(y<.83){const centre=Math.sign(x)*(.10+(1.2-y)*.25);p.setX(i,centre+(x-centre)*.67);p.setZ(i,.04+(p.getZ(i)-.04)*.78)}}g.computeVertexNormals();}
    }
    if(appearance.version==='2'&&appearance.style==='buzz-cut'&&object.name==='hair'){const g=object.geometry.clone();ownedGeometry.add(g);object.geometry=g;delete g.userData.shared;const p=g.getAttribute('position');for(let i=0;i<p.count;i++){if(p.getY(i)>2.24)p.setY(i,2.24+(p.getY(i)-2.24)*.45)}g.computeVertexNormals();}
    if(appearance.version==='2'&&appearance.figure==='soft'&&['casual-clothing','pants'].includes(object.name)){const g=object.geometry.clone();ownedGeometry.add(g);object.geometry=g;delete g.userData.shared;const p=g.getAttribute('position');for(let i=0;i<p.count;i++)if(p.getY(i)>1.05&&p.getY(i)<1.90)p.setX(i,p.getX(i)*1.08);g.computeVertexNormals();}
    if(appearance.version==='2'&&['skin','eyes'].includes(object.name)){
     const geometry=object.geometry.clone();ownedGeometry.add(geometry);object.geometry=geometry;delete geometry.userData.shared;
     const positions=geometry.getAttribute('position');
     for(let i=0;i<positions.count;i++){
      let x=positions.getX(i),y=positions.getY(i),z=positions.getZ(i);
      if(y>1.98){
       if(appearance.face==='round')x*=1.07;else if(appearance.face==='angular'&&y<2.15)x*=.92;
       if(object.name==='eyes'){const factor=appearance.eyes==='round'?1.16:appearance.eyes==='narrow'?.8:1;y=2.13+(y-2.13)*factor;}
       if(z>.13&&Math.abs(x)<.045&&y>2.10&&y<2.20){if(appearance.nose==='wide')x*=1.16;if(appearance.nose==='soft')z-=.009}
       if(z>.11&&Math.abs(x)<.065&&y>2.03&&y<2.10){if(appearance.mouth==='full')z+=.008;if(appearance.mouth==='smile')y+=Math.abs(x)*.12}
       if(z>.10&&y>2.15&&y<2.19&&Math.abs(x)>.025&&Math.abs(x)<.10){if(appearance.brows==='arched')y+=.009*Math.sin(Math.abs(x)*35);if(appearance.brows==='straight')y=2.17+(y-2.17)*.5}
      }else if(appearance.figure==='soft'&&y>1.25&&y<1.8)x*=1.07;
      positions.setXYZ(i,x,y,z);
     }
     geometry.computeVertexNormals();geometry.computeBoundingSphere();
    }
   });
   let far:T.Group|undefined,closed=false;
   root.userData.animate=(time:number,speed:number,mode?:string)=>{if(closed)return;if(model.visible)pose.animate(time,speed,mode,root.userData.emote,root.userData.speaking);else if(far){far.userData.emote=root.userData.emote;far.userData.speaking=root.userData.speaking;far.userData.animate(time,speed,mode)}};
   root.userData.sit=()=>{if(!closed){if(model.visible)pose.sit();else far?.userData.sit()}};
   root.userData.cycle=(time:number,speed:number)=>{if(!closed){if(model.visible)pose.cycle(time,speed);else far?.userData.cycle(time,speed)}};
   root.userData.swim=(time:number)=>{if(!closed){if(model.visible)pose.swim(time);else far?.userData.swim(time)}};
   root.userData.setLOD=(distance:number)=>{
    if(closed)return;
    model.visible=distance<35;
    if(!model.visible&&!far){far=fallback(appearance,calibrated);far.userData.setLOD(80);root.add(far)}
    if(far)far.visible=!model.visible;
   };
   const close=()=>{
    if(closed)return;closed=true;wardrobe?.dispose();
    for(const skeleton of skeletons)skeleton.dispose();
    for(const material of ownedMaterials)material.dispose();
    for(const geometry of ownedGeometry)geometry.dispose();
    far?.userData.dispose?.();
    root.clear();instances.delete(close);
   };
   root.userData.dispose=close;instances.add(close);
   return root;
  },
  dispose(){
   if(disposed)return;disposed=true;
   for(const close of [...instances])close();
   for(const geometry of geometries)geometry.dispose();
   for(const material of materials)material.dispose();
   for(const texture of textures)texture.dispose();
   const skeletons=new Set<T.Skeleton>();template.traverse(o=>{if(o instanceof T.SkinnedMesh)skeletons.add(o.skeleton)});
   for(const skeleton of skeletons)skeleton.dispose();
  },
  metrics(){return {instances:instances.size,geometries:geometries.size,textures:textures.size,disposed}},
 };
}
