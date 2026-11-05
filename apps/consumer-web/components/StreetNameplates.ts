import * as T from 'three';
import {streetPlates} from '../lib/streetNames.ts';
import {streetSign} from './WorldAssets.ts';
type Label={object:T.Object3D;text:string;kind:string};
export function streetNameplates(parent:T.Object3D,features:Parameters<typeof streetPlates>[0],labels:Label[]){
 const plates=streetPlates(features),active=new Map<string,{group:T.Group;label:Label}>();let key='';
 const remove=(id:string)=>{const entry=active.get(id);if(!entry)return;entry.group.removeFromParent();const index=labels.indexOf(entry.label);if(index>=0)labels.splice(index,1);const geometries=new Set<T.BufferGeometry>(),materials=new Set<T.Material>();entry.group.traverse(o=>{if(o instanceof T.Mesh&&!o.geometry.userData.shared){geometries.add(o.geometry);for(const m of Array.isArray(o.material)?o.material:[o.material])materials.add(m)}});geometries.forEach(g=>g.dispose());materials.forEach(m=>{if(m instanceof T.MeshBasicMaterial)m.map?.dispose();m.dispose()});active.delete(id)};
 return {update(point:{x:number;z:number}){const next=Math.floor(point.x/25)+','+Math.floor(point.z/25);if(next===key)return;key=next;const nearby=plates.filter(p=>Math.hypot(p.x-point.x,p.z-point.z)<135).sort((a,b)=>Math.hypot(a.x-point.x,a.z-point.z)-Math.hypot(b.x-point.x,b.z-point.z)).slice(0,28);const keep=new Set(nearby.map(p=>p.key));for(const id of active.keys())if(!keep.has(id))remove(id);for(const p of nearby)if(!active.has(p.key)){const group=streetSign(parent,p.name,p.x,p.z,p.angle);const label={object:group,text:p.name,kind:'street'};labels.push(label);active.set(p.key,{group,label})}},dispose(){for(const id of active.keys())remove(id)},metrics(){return{sourceNames:new Set(plates.map(p=>p.name)).size,indexedPlates:plates.length,activePlates:active.size}}};
}
