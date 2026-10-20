import * as T from 'three';
type Feature={id:string;tags:Record<string,string>;points:number[][]};
export type SignSpec={id:string;name:string;x:number;z:number;angle:number;width:number;category:string;source_id?:string};
const distance=(a:number[],b:number[])=>Math.hypot(a[0]-b[0],a[1]-b[1]);
function inside(p:number[],points:number[][]){let yes=false;for(let i=0,j=points.length-1;i<points.length;j=i++){const a=points[i],b=points[j];if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])yes=!yes}return yes}
function centroid(f:Feature){return f.points.reduce((a,p)=>[a[0]+p[0]/f.points.length,a[1]+p[1]/f.points.length],[0,0])}
function segmentDistance(p:number[],a:number[],b:number[]){const dx=b[0]-a[0],dz=b[1]-a[1],t=Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dz)/(dx*dx+dz*dz||1)));return distance(p,[a[0]+t*dx,a[1]+t*dz])}
export function buildingSignSpecs(features:Feature[]):SignSpec[]{
 const buildings=features.filter(f=>f.tags.building&&f.points.length>=4),roads=features.filter(f=>f.tags.highway&&f.points.length>1);const specs:SignSpec[]=[];const assigned=new Set<string>();
 for(const named of features.filter(f=>f.tags.name&&!f.tags.highway&&(f.tags.building||f.tags.shop||f.tags.amenity))){
  const point=centroid(named);let building=named.tags.building?named:buildings.find(b=>inside(point,b.points));

  if(!building||assigned.has(building.id)||(building.tags.shop==='mall'&&named.id!==building.id))continue;
  const edges=building.points.slice(0,-1).map((a,i)=>{const b=building!.points[i+1],length=distance(a,b),mid=[(a[0]+b[0])/2,(a[1]+b[1])/2];let nx=(b[1]-a[1])/(length||1),nz=-(b[0]-a[0])/(length||1);if(inside([mid[0]+nx*.1,mid[1]+nz*.1],building!.points)){nx=-nx;nz=-nz}let street=Infinity;for(const r of roads)for(let j=1;j<r.points.length;j++)street=Math.min(street,segmentDistance(mid,r.points[j-1],r.points[j]));return {mid,length,nx,nz,street}}).filter(e=>e.length>=2).sort((a,b)=>a.street-b.street||b.length-a.length);
  const edge=edges[0];if(!edge)continue;assigned.add(building.id);specs.push({id:building.id,source_id:named.tags.shop||['cafe','restaurant','bank','pharmacy','pub','fast_food'].includes(named.tags.amenity)?named.id:undefined,name:named.tags.name,x:edge.mid[0]+edge.nx*.28,z:edge.mid[1]+edge.nz*.28,angle:Math.atan2(edge.nx,edge.nz),width:Math.min(8,edge.length*.8),category:named.tags.shop||named.tags.amenity||'Building'});
 }
 return specs;
}
export function buildingSign(spec:SignSpec){
 const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=144;const c=canvas.getContext('2d')!;c.fillStyle='#173449';c.fillRect(0,0,1024,144);c.strokeStyle='#87bece';c.lineWidth=8;c.strokeRect(6,6,1012,132);c.fillStyle='#f3f6ed';c.textAlign='center';c.textBaseline='middle';let size=68;c.font=`600 ${size}px sans-serif`;while(c.measureText(spec.name).width>940&&size>18){size-=2;c.font=`600 ${size}px sans-serif`}c.fillText(spec.name,512,72);
 const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;const material=new T.MeshBasicMaterial({map:texture});const mesh=new T.Mesh(new T.PlaneGeometry(spec.width,.72),material);mesh.position.set(spec.x,3.1,spec.z);mesh.rotation.y=spec.angle;mesh.userData.item={source_id:spec.source_id,title:spec.name,category:spec.category,x:spec.x,z:spec.z,description:'OpenStreetMap building. This nameplate does not imply a participating merchant or reward.'};mesh.userData.dispose=()=>{mesh.geometry.dispose();material.dispose();texture.dispose()};return mesh;
}
