import {contains} from './whitehouseArchitecture.ts';
type Feature={id:string;tags:Record<string,string>;points:number[][];holes?:number[][][]};
export type StreetPlate={key:string;name:string;x:number;z:number;angle:number};
/** Source names only, spaced along long roads. No spawn-relative name limit. */
export function streetPlates(features:Feature[]):StreetPlate[]{
 const buildings=features.filter(f=>f.tags.building&&f.points.length>3),plates:StreetPlate[]=[];
 const byName=new Map<string,StreetPlate[]>();
 for(const f of features){const name=f.tags.name||f.tags['name:en'];if(!f.tags.highway||!name||f.points.length<2)continue;
  for(let i=1;i<f.points.length;i++){
   const a=f.points[i-1],b=f.points[i],dx=b[0]-a[0],dz=b[1]-a[1],length=Math.hypot(dx,dz);if(length<3)continue;
   const steps=Math.max(1,Math.ceil(length/130)),width=Math.min(14,Math.max(3,parseFloat(f.tags.width)||Number(f.tags.lanes||2)*3));
   for(let n=0;n<steps;n++){const t=(n+.5)/steps,cx=a[0]+dx*t,cz=a[1]+dz*t;
    if((byName.get(name)||[]).some(p=>Math.hypot(p.x-cx,p.z-cz)<100))continue;
    const nx=dz/length,nz=-dx/length;let point:number[]|undefined;
    for(const sign of [1,-1]){const candidate=[cx+nx*(width/2+2.5)*sign,cz+nz*(width/2+2.5)*sign];if(!buildings.some(f=>contains(candidate,f.points)&&!f.holes?.some(h=>contains(candidate,h)))){point=candidate;break}}
    if(!point)continue;const plate={key:f.id+':'+i+':'+n,name,x:point[0],z:point[1],angle:Math.atan2(nx,nz)};plates.push(plate);const named=byName.get(name)||[];named.push(plate);byName.set(name,named);
   }
  }
 }
 return plates;
}
