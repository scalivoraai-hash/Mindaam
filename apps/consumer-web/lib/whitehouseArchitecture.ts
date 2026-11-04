import {buildingStyle} from './buildingStyle.ts';

export type ArchitecturalFeature={id:string;tags:Record<string,string>;points:number[][];holes?:number[][][]};
export function contains(point:number[],ring:number[][]){
 let result=false;
 for(let i=0,j=ring.length-1;i<ring.length;j=i++){
  const a=ring[i],b=ring[j];
  if((a[1]>point[1])!==(b[1]>point[1])&&point[0]<(b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0])result=!result;
 }
 return result;
}

/** A contained mapped POI can inform ground-floor styling, never ownership/use data. */
export function whitehouseArchitecture(building:ArchitecturalFeature,pois:ArchitecturalFeature[],residential:ArchitecturalFeature[]){
 const original=buildingStyle(building.tags,building.id);
 const contained=pois.filter(p=>p.points.length===1&&contains(p.points[0],building.points)&&!building.holes?.some(h=>contains(p.points[0],h)));
 const commercial=contained.find(p=>['shop','office'].includes(buildingStyle(p.tags,p.id).family));
 const source=commercial||contained.find(p=>buildingStyle(p.tags,p.id).family==='civic');
 const family=original.family==='neutral'&&source?buildingStyle(source.tags,source.id).family:original.family;
 const centre=building.points.slice(0,-1).reduce((sum,p)=>[sum[0]+p[0]/(building.points.length-1),sum[1]+p[1]/(building.points.length-1)],[0,0]);
 const residentialContext=family==='home'||(family==='neutral'&&residential.some(f=>contains(centre,f.points)&&!f.holes?.some(h=>contains(centre,h))));
 return {...original,family,residentialContext,poi:source?.id||null,name:building.tags.name||source?.tags.name||'',
  confidence:source?'contained mapped POI':original.family!=='neutral'?'mapped building tags':residentialContext?'regional residential approximation; use unverified':'neutral approximation; use unverified'};
}

/** Locate a facade facing a nearby mapped route; never infer a driveway/hitbox. */
export function frontageEdge(points:number[][],segments:number[][][]){
 const ring=points.length>1&&points[0][0]===points.at(-1)![0]&&points[0][1]===points.at(-1)![1]?points.slice(0,-1):points;
 const area=ring.reduce((sum,a,i)=>{const b=ring[(i+1)%ring.length];return sum+a[0]*b[1]-b[0]*a[1]},0);
 let best=Infinity,index=0;
 for(let i=0;i<ring.length;i++){
  const a=ring[i],b=ring[(i+1)%ring.length],x=(a[0]+b[0])/2,z=(a[1]+b[1])/2,dx=b[0]-a[0],dz=b[1]-a[1],sign=area>0?-1:1;
  for(const [start,end] of segments){
   const sx=end[0]-start[0],sz=end[1]-start[1],length=sx*sx+sz*sz;
   const t=length?Math.max(0,Math.min(1,((x-start[0])*sx+(z-start[1])*sz)/length)):0;
   const vx=start[0]+sx*t-x,vz=start[1]+sz*t-z,distance=vx*vx+vz*vz;
   if((-dz*vx+dx*vz)*sign<=0||distance>1600)continue;
   if(distance<best){best=distance;index=i}
  }
 }
 return index;
}
