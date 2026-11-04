import {BufferGeometry, Float32BufferAttribute, LineBasicMaterial, LineSegments, Object3D} from 'three';
import {box} from './WorldAssets.ts';

// One shared radial spoke mesh per wheel. Rotate only the detail around the local axle.
const spokes = new BufferGeometry();
const vertices:number[]=[];
for(let i=0;i<12;i++){
 const angle=i*Math.PI/6;
 vertices.push(0,0,0,0,Math.cos(angle),Math.sin(angle));
}
spokes.setAttribute('position',new Float32BufferAttribute(vertices,3));
const alloy=new LineBasicMaterial({color:'#c5cbd0'});

export function detailVehicle(model:Object3D,kind:string){
 const wheels:LineSegments[]=[];
 const wheel=(x:number,y:number,z:number,radius:number,outerRadius:number)=>{
  const rim=new LineSegments(spokes,alloy);
  rim.position.set(x,y,z);
  rim.scale.setScalar(radius);
  rim.userData.outerRadius=outerRadius;
  model.add(rim);
  wheels.push(rim);
 };
 if(kind==='car'||kind==='bus'){
  const bus=kind==='bus';
  for(const side of [-1,1]){
   for(const z of bus?[-2.15,2.12]:[-1.25,1.28]){
    wheel(side*(bus?1.352:1.055),bus?.5:.4,z,bus?.26:.22,bus?.5:.37);
   }
   box(model,'#efb33c',side*(bus?1.25:.94),bus?1.12:.85,bus?2.88:1.6,.025,.07,.12);
  }
  box(model,'#e4bb4e',0,bus?.95:.67,bus?-3.55:-2.09,.52,.12,.02);
 }else if(['bike','ebike','scooter','motorbike'].includes(kind)){
  const bicycle=kind==='bike'||kind==='ebike';
  for(const z of bicycle?[-.8,.8]:[-.83,.88]){
   if(bicycle)wheel(0,.5,z,.43,.48);
   else for(const side of [-1,1])wheel(side*.109,.44,z,.27,.42);
  }
  if(bicycle)box(model,'#bd352c',0,1.06,-.49,.12,.06,.035);
  else box(model,'#c0c2bf',.26,.56,-.48,.12,.14,.64);
 }
 model.userData.rollWheels=(distance:number)=>{
  for(const rim of wheels)rim.rotation.x+=distance/rim.userData.outerRadius;
 };
}
