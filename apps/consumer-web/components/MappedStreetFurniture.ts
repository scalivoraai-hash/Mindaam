import * as T from 'three';
import {trafficSignalPhase} from '../lib/trafficSignalPhase.ts';
type Feature={id:string;tags:Record<string,string>;points:number[][]};
/** Mapped nodes only. Signals are visual states, not a new driving authority. */
export function mappedStreetFurniture(parent:T.Object3D,features:Feature[]){
 const root=new T.Group();root.name='Mapped street furniture';parent.add(root);const cube=new T.BoxGeometry(1,1,1),orb=new T.SphereGeometry(1,8,6),materials=new Map<string,T.MeshStandardMaterial>(),matrices=new Map<string,T.Matrix4[]>();
 const transform=new T.Object3D();const material=(color:string)=>{if(!materials.has(color))materials.set(color,new T.MeshStandardMaterial({color,roughness:.70}));return materials.get(color)!};
 const block=(color:string,x:number,y:number,z:number,w:number,h:number,d:number)=>{transform.position.set(x,y,z);transform.scale.set(w,h,d);transform.updateMatrix();const list=matrices.get(color)||[];list.push(transform.matrix.clone());matrices.set(color,list)};
 const lampMatrices:T.Matrix4[]=[],signals:{lamps:number[];axis:0|1}[]=[],counts:Record<string,number>={};
 for(const f of features){if(f.points.length!==1)continue;const [x,z]=f.points[0],t=f.tags;let kind='';
  if(t.highway==='traffic_signals'){
   kind='traffic_signals';block('#42515b',x,1.8,z,.09,3.6,.09);block('#1c2931',x,3.2,z,.34,.90,.22);
   let nearest=Infinity,angle=0;
   for(const road of features){if(!road.tags.highway||road.points.length<2)continue;for(let i=1;i<road.points.length;i++){const a=road.points[i-1],b=road.points[i],dx=b[0]-a[0],dz=b[1]-a[1],length=dx*dx+dz*dz;if(!length)continue;const t=Math.max(0,Math.min(1,((x-a[0])*dx+(z-a[1])*dz)/length)),distance=Math.hypot(x-a[0]-t*dx,z-a[1]-t*dz);if(distance<nearest){nearest=distance;angle=Math.atan2(dx,dz)}}}
   const axis:0|1=Math.abs(Math.sin(angle))>.7?1:0,lamps:number[]=[];
   for(let i=0;i<3;i++){transform.position.set(x,3.46-i*.26,z+.13);transform.scale.set(.10,.10,.035);transform.updateMatrix();lamps.push(lampMatrices.length);lampMatrices.push(transform.matrix.clone())}signals.push({lamps,axis});
  }else if(t.highway==='street_lamp'){
   kind='street_lamp';block('#4c5b5f',x,2.5,z,.08,5,.08);block('#e7e2c9',x,5,z+.32,.35,.08,.85);
  }else if(t.amenity==='bench'){
   kind='bench';for(const side of [-.7,.7])block('#394a4d',x+side,.3,z,.08,.60,.48);for(let i=0;i<3;i++){block('#9f8061',x,.60,z+i*.14,1.8,.08,.11);block('#9f8061',x,.88+i*.13,z-.09,1.8,.09,.06)}
  }else if(t.highway==='bus_stop'||t.railway==='tram_stop'){
   kind=t.highway==='bus_stop'?'bus_stop':'tram_stop';block('#394a4d',x,1.5,z,.08,3,.08);block('#e2e5de',x,2.75,z,.55,.5,.08);block('#466b87',x,2.75,z+.05,.37,.16,.02);
  }else if(t.amenity==='waste_basket'){
   kind='waste_basket';block('#4e625b',x,.45,z,.44,.90,.44);block('#253b32',x,.92,z,.48,.07,.48);
  }else if(t.barrier==='bollard'){
   kind='bollard';block('#69767b',x,.45,z,.12,.90,.12);block('#e8dfbb',x,.74,z,.13,.06,.13);
  }
  if(kind)counts[kind]=(counts[kind]||0)+1;
 }
 for(const [color,list] of matrices){const mesh=new T.InstancedMesh(cube,material(color),list.length);list.forEach((m,i)=>mesh.setMatrixAt(i,m));mesh.computeBoundingSphere();root.add(mesh)}
 const bulbs=new T.InstancedMesh(orb,material('#ffffff'),lampMatrices.length);lampMatrices.forEach((m,i)=>{bulbs.setMatrixAt(i,m);bulbs.setColorAt(i,new T.Color('#17202a'))});bulbs.computeBoundingSphere();root.add(bulbs);
 // Opposing display axes never show green together; all-red clearance separates phases.
 // The cycles are a visual approximation, not surveyed timing or driving authority.
 let last=-1;
 return {counts,update(seconds:number){const second=Math.floor(seconds);if(second===last)return;last=second;for(const signal of signals){const state=trafficSignalPhase(seconds,signal.axis);signal.lamps.forEach((lamp,i)=>{const active=['red','amber','green'][i]===state;bulbs.setColorAt(lamp,new T.Color(active?['#e64236','#e8b74b','#3dbb7b'][i]:'#17202a'))})}if(bulbs.instanceColor)bulbs.instanceColor.needsUpdate=true},dispose(){root.removeFromParent();root.traverse(o=>{if(o instanceof T.InstancedMesh)o.dispose()});cube.dispose();orb.dispose();materials.forEach(m=>m.dispose())}};
}
