import * as T from 'three';
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
   if(appearance.style&&appearance.style!=='short')return fallback(appearance,calibrated);
   const root=new T.Group(),model=clone(template);root.add(model);
   // Validate before allocating per-instance materials. A rejected rig owns no GPU resources.
   const pose=cinematicCharacterPose(model,calibrated);
   const ownedMaterials=new Set<T.Material>(),skeletons=new Set<T.Skeleton>();
   const colors:Record<string,string|undefined>={skin:appearance.skin,hair:appearance.hair,'casual-clothing':appearance.color,pants:appearance.pants};
   model.traverse(object=>{
    if(!(object instanceof T.Mesh))return;
    object.castShadow=true;object.receiveShadow=true;
    const copy=(source:T.Material)=>{
     const material=source.clone();ownedMaterials.add(material);
     if(material instanceof T.MeshStandardMaterial&&colors[material.name])material.color.set(colors[material.name]!);
     return material;
    };
    object.material=Array.isArray(object.material)?object.material.map(copy):copy(object.material);
    if(object instanceof T.SkinnedMesh)skeletons.add(object.skeleton);
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
    if(closed)return;closed=true;
    for(const skeleton of skeletons)skeleton.dispose();
    for(const material of ownedMaterials)material.dispose();
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
