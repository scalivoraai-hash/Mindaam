import * as T from 'three';
import {mergeGeometries} from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import {whitehouseArchitecture,frontageEdge} from '../lib/whitehouseArchitecture.ts';

type Feature={id:string;tags:Record<string,string>;points:number[][];holes?:number[][][]};
type Geography={features:Feature[]};
type Building={feature:Feature;x:number;z:number};
const TILE=80;
const BRICKS=['#a6745a','#b18e73','#d5c7ac','#846658'];

/** Original deterministic brick/roof artwork. No downloaded or proprietary assets. */
function masonryTexture(roof=false){
 const canvas=document.createElement('canvas');canvas.width=512;canvas.height=512;
 const ctx=canvas.getContext('2d');if(!ctx)throw Error('Cinematic material canvas unavailable');
 ctx.fillStyle=roof?'#686a69':'#c6b9a5';ctx.fillRect(0,0,512,512);
 let seed=7139;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296};
 const h=roof?64:32,w=roof?64:96;
 for(let row=0;row<512/h;row++)for(let col=-1;col<512/w+1;col++){
  const x=col*w+(row%2)*w/2,y=row*h,n=Math.floor(145+random()*38);
  ctx.fillStyle=`rgb(${n},${n-5},${n-12})`;ctx.fillRect(x+2,y+2,w-4,h-4);
  ctx.fillStyle='rgba(20,16,12,.18)';ctx.fillRect(x+2,y+h-5,w-4,2);
  for(let i=0;i<45;i++){const q=random();ctx.fillStyle=q>.5?'rgba(255,255,240,.12)':'rgba(40,30,22,.10)';ctx.fillRect(x+random()*w,y+random()*h,1+random()*3,1)}
 }
 const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;
 texture.wrapS=texture.wrapT=T.RepeatWrapping;texture.anisotropy=4;return texture;
}

/** Extra visual surfaces only: never changes authoritative footprints or movement.
 * All mapped buildings are indexed. Nearby tiles are constructed incrementally and
 * evicted; the existing complete district remains underneath as a safe far LOD.
 */
export function cinematicDistrict(parent:T.Object3D,geo:Geography){
 const root=new T.Group();root.name='Whitehouse cinematic details';parent.add(root);
 const brick=masonryTexture(),roofTexture=masonryTexture(true);
 const walls=BRICKS.map(color=>new T.MeshStandardMaterial({color,map:brick,roughness:.91}));
 const roofMaterial=new T.MeshStandardMaterial({color:'#55565b',map:roofTexture,roughness:.85,side:T.DoubleSide});
 const trim=new T.MeshStandardMaterial({color:'#dbd9cd',roughness:.65});
 const metal=new T.MeshStandardMaterial({color:'#393e42',roughness:.5,metalness:.35});
 const glass=new T.MeshStandardMaterial({color:'#294552',roughness:.24,metalness:.28,emissive:'#e7bb79',emissiveIntensity:0});
 const door=new T.MeshStandardMaterial({color:'#334c50',roughness:.65});
 const materials=[...walls,roofMaterial,trim,metal,glass,door];
 const cube=new T.BoxGeometry(1,1,1);const matrix=new T.Matrix4(),rotation=new T.Quaternion();
 const position=new T.Vector3(),scale=new T.Vector3();
 const tiles=new Map<string,Building[]>(),active=new Map<string,T.Group>();
 const residential=geo.features.filter(f=>f.tags.landuse==='residential'&&f.points.length>=4);
 const pois=geo.features.filter(f=>f.points.length===1&&(f.tags.shop||f.tags.amenity||f.tags.office));
 const routes=new Map<string,number[][][]>();
 for(const f of geo.features){if(!f.tags.highway||['motorway','trunk','motorway_link','trunk_link'].includes(f.tags.highway))continue;for(let i=1;i<f.points.length;i++){const segment=[f.points[i-1],f.points[i]];for(let x=Math.floor(Math.min(segment[0][0],segment[1][0])/TILE);x<=Math.floor(Math.max(segment[0][0],segment[1][0])/TILE);x++)for(let z=Math.floor(Math.min(segment[0][1],segment[1][1])/TILE);z<=Math.floor(Math.max(segment[0][1],segment[1][1])/TILE);z++){const key=x+','+z,list=routes.get(key)||[];list.push(segment);routes.set(key,list)}}}
 for(const feature of geo.features){
  if(!feature.tags.building||feature.points.length<4)continue;
  const points=feature.points.slice(0,-1),x=points.reduce((s,p)=>s+p[0],0)/points.length,z=points.reduce((s,p)=>s+p[1],0)/points.length;
  const key=`${Math.floor(x/TILE)},${Math.floor(z/TILE)}`;const list=tiles.get(key)||[];list.push({feature,x,z});tiles.set(key,list);
 }
 let disposed=false,failed=false,lastKey='',pending:string[]=[],builds=0;
 const release=(group:T.Group)=>group.traverse(o=>{if(o instanceof T.InstancedMesh)o.dispose();if(o instanceof T.Mesh){if(o.geometry!==cube)o.geometry.dispose();if(o.userData.cinematicSign){const material=o.material as T.MeshStandardMaterial;material.map?.dispose();material.dispose()}}});
 const remove=(key:string)=>{const group=active.get(key);if(!group)return;root.remove(group);release(group);active.delete(key)};
 function tile(key:string){
  const [ix,iz]=key.split(',').map(Number),ox=ix*TILE,oz=iz*TILE;
  const group=new T.Group();group.position.set(ox,0,oz);
  const solids=new Map<T.Material,T.Matrix4[]>(),surfaces=new Map<T.Material,T.BufferGeometry[]>();
  function block(material:T.Material,x:number,y:number,z:number,w:number,h:number,d:number,angle:number){
   position.set(x-ox,y,z-oz);scale.set(w,h,d);rotation.setFromAxisAngle(T.Object3D.DEFAULT_UP,angle);
   matrix.compose(position,rotation,scale);const list=solids.get(material)||[];list.push(matrix.clone());solids.set(material,list);
  }
  function surface(material:T.Material,vertices:number[],uv:number[]){
   const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(vertices,3));geometry.setAttribute('uv',new T.Float32BufferAttribute(uv,2));geometry.computeVertexNormals();
   const list=surfaces.get(material)||[];list.push(geometry);surfaces.set(material,list);
  }
  try{
   for(const {feature:f,x:cx,z:cz} of tiles.get(key)||[]){
    const style=whitehouseArchitecture(f,pois,residential),height=style.height,points=f.points.slice(0,-1),residentialContext=style.residentialContext;
    const nearby=new Set<number[][]>();for(let dx=-1;dx<=1;dx++)for(let dz=-1;dz<=1;dz++)for(const segment of routes.get((Math.floor(cx/TILE)+dx)+','+(Math.floor(cz/TILE)+dz))||[])nearby.add(segment);
    const front=frontageEdge(f.points,[...nearby]);
    const commercial=style.family==='shop'||style.family==='office';
    const wallMaterial=walls[style.hash%walls.length];
    // Keep holes/open courtyards untouched; never cap an irregular footprint with a box.
    for(let i=0;i<points.length;i++){
     const a=points[i],b=points[(i+1)%points.length],dx=b[0]-a[0],dz=b[1]-a[1],length=Math.hypot(dx,dz);if(length<1.5)continue;
     const tx=dx/length,tz=dz/length;let nx=-tz,nz=tx;
     // Polygon winding, rather than a centroid normal, handles concave facades.
     const area=points.reduce((s,p,j)=>s+p[0]*points[(j+1)%points.length][1]-points[(j+1)%points.length][0]*p[1],0);
     if(area>0){nx=-nx;nz=-nz}
     const angle=Math.atan2(nx,nz),x=(a[0]+b[0])/2,z=(a[1]+b[1])/2;
     const local=(u:number,y:number,out:number)=>[x+tx*u+nx*out-ox,y,z+tz*u+nz*out-oz];
     const p0=local(-length/2,.03,.035),p1=local(length/2,.03,.035),p2=local(length/2,height,.035),p3=local(-length/2,height,.035);
     // Double-sided avoids winding assumptions while the base shell preserves collision.
     wallMaterial.side=T.DoubleSide;
     surface(wallMaterial,[...p0,...p1,...p2,...p0,...p2,...p3],[0,0,length/2,0,length/2,height/2,0,0,length/2,height/2,0,height/2]);
     const put=(m:T.Material,u:number,y:number,out:number,w:number,h:number,d:number)=>block(m,x+tx*u+nx*out,y,z+tz*u+nz*out,w,h,d,angle);
     if(commercial&&i===front&&length>3){
      const width=Math.min(6,length-.6);
      // A visual canopy stays above pedestrian headroom; no new collider or business.
      put(metal,0,2.75,.48,width,.10,.9);
      put(door,0,2.66,.90,width,.17,.07);
      if(style.name){
       const canvas=document.createElement('canvas');canvas.width=512;canvas.height=64;
       const ctx=canvas.getContext('2d');if(!ctx)throw Error('Shopfront canvas unavailable');
       ctx.fillStyle='#203d3b';ctx.fillRect(0,0,512,64);ctx.fillStyle='#f3ead5';
       ctx.font=`600 ${Math.min(30,Math.floor(850/Math.max(1,style.name.length)))}px sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(style.name,256,33,490);
       const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;
       const material=new T.MeshStandardMaterial({map:texture,roughness:.75,side:T.DoubleSide});
       const sign=new T.Mesh(new T.PlaneGeometry(width,.58),material);sign.position.set(x+nx*.28-ox,3.12,z+nz*.28-oz);sign.rotation.y=angle;sign.userData.cinematicSign=true;group.add(sign);
      }
     }
     put(metal,0,height+.05,.10,length,.11,.14); // gutter/fascia
     put(metal,-length/2+.16,height/2,.10,.075,height,.075);
     put(trim,0,.16,.08,length,.26,.15);
     if(style.family==='utility'){if(i===front&&length>4){put(metal,0,1.55,.12,Math.min(4,length-1),3,.10);for(let y=.35;y<3;y+=.3)put(trim,0,y,.18,Math.min(4,length-1),.025,.025)}continue;}
     const floors=Math.min(7,Math.max(1,Math.floor(height/3.1))),bays=Math.min(12,Math.max(1,Math.floor(length/(commercial?3:2.7))));
     for(let floor=0;floor<floors;floor++)for(let bay=0;bay<bays;bay++){
      const u=(bay+.5)*length/bays-length/2,w=Math.min(commercial&&floor===0?2.15:1.15,length/bays-.65),y=1.65+floor*3.1,h=commercial&&floor===0?2.35:1.35;
      if(w<.45||y+h/2>height-.3)continue;
      const entrance=floor===0&&bay===Math.floor(bays/2)&&i===front;
      if(entrance){put(trim,u,1.16,.11,1.1,2.3,.18);put(door,u,1.13,.215,.91,2.18,.045);put(glass,u,1.65,.245,.57,.65,.025);put(metal,u+.3,1.05,.27,.035,.18,.04);continue}
      put(metal,u,y,.09,w+.16,h+.16,.09);put(glass,u,y,.145,w,h,.025);
      for(const side of [-1,1]){put(trim,u+side*w/2,y,.185,.065,h+.14,.10);put(trim,u,y+side*h/2,.185,w+.12,.065,.10)}
      put(trim,u,y,.19,.045,h,.08);put(trim,u,y-h/2-.07,.21,w+.23,.09,.30);
      if(style.family==='apartments'&&floor>0&&i===front&&bay%2===0){
       put(trim,u,y-.83,.48,w+.4,.10,.85);
       put(metal,u,y-.36,.89,w+.38,.045,.045);
       for(let bar=-2;bar<=2;bar++)put(metal,u+bar*(w+.3)/4,y-.58,.89,.025,.47,.025);
      }
     }
    }
    // Regional roof approximation only for rectangular residential-context buildings.
    if(residentialContext&&f.tags['roof:shape']!=='flat'&&points.length===4&&!f.holes?.length&&height<13){
     const [a,b,d]=[points[0],points[1],points[3]],ux=b[0]-a[0],uz=b[1]-a[1],vx=d[0]-a[0],vz=d[1]-a[1],w=Math.hypot(ux,uz),depth=Math.hypot(vx,vz);
     if(w>1&&depth>1&&Math.abs(ux*vx+uz*vz)/(w*depth)<.06){
      const corners=points.map(p=>[p[0]-ox,height+.25,p[1]-oz]),first=w<depth?[0,1]:[0,3],second=w<depth?[3,2]:[1,2];
      const mid=(ids:number[])=>[(corners[ids[0]][0]+corners[ids[1]][0])/2,height+Math.min(2.8,Math.min(w,depth)*.32),(corners[ids[0]][2]+corners[ids[1]][2])/2];
      const r=mid(first),q=mid(second),[p0,p1]=first.map(i=>corners[i]),[p3,p2]=second.map(i=>corners[i]);
      const verts=[p0,p1,r,p3,q,p2,p0,r,q,p0,q,p3,p1,p2,q,p1,q,r];
      surface(roofMaterial,verts.flat(),verts.flatMap(p=>[p[0]/2,p[2]/2+p[1]/3]));
     }
    }
   }
   for(const [material,transforms] of solids){const mesh=new T.InstancedMesh(cube,material,transforms.length);transforms.forEach((m,i)=>mesh.setMatrixAt(i,m));mesh.computeBoundingSphere();mesh.receiveShadow=true;group.add(mesh)}
   for(const [material,geometries] of surfaces){const merged=mergeGeometries(geometries,false);if(!merged)throw Error('Incompatible cinematic surfaces');const mesh=new T.Mesh(merged,material);mesh.receiveShadow=true;mesh.castShadow=true;group.add(mesh)}
   root.add(group);active.set(key,group);builds++;
  }catch(error){release(group);throw error}
  finally{for(const geometries of surfaces.values())for(const g of geometries)g.dispose()}
 }
 return {
  update(point:{x:number;z:number},quality:string,night=0,rain=0){
   if(disposed||failed)return;
   glass.emissiveIntensity=Math.max(0,Math.min(1,night))*.38;
   roofMaterial.roughness=.85-Math.max(0,Math.min(1,rain))*.25;
   try{
    const x=Math.floor(point.x/TILE),z=Math.floor(point.z/TILE),key=`${x},${z}:${quality}`;
    if(key!==lastKey){lastKey=key;const radius=quality==='high'?2:1;const selected:string[]=[];
     for(let dx=-radius;dx<=radius;dx++)for(let dz=-radius;dz<=radius;dz++){const id=`${x+dx},${z+dz}`;if(tiles.has(id))selected.push(id)}
     selected.sort((a,b)=>{const distance=(id:string)=>{const [ix,iz]=id.split(',').map(Number);return (ix-x)**2+(iz-z)**2};return distance(a)-distance(b)});
     const keep=new Set(selected);for(const id of active.keys())if(!keep.has(id))remove(id);pending=selected.filter(id=>!active.has(id));
    }
    const next=pending.shift();if(next)tile(next);
   }catch{failed=true;for(const id of active.keys())remove(id);pending=[];console.warn('Cinematic details unavailable; standard district retained')}
  },
  metrics:()=>({indexedBuildings:[...tiles.values()].reduce((n,b)=>n+b.length,0),activeTiles:active.size,pendingTiles:pending.length,builtTiles:builds,failed}),
  dispose(){if(disposed)return;disposed=true;for(const id of active.keys())remove(id);parent.remove(root);cube.dispose();brick.dispose();roofTexture.dispose();materials.forEach(m=>m.dispose());pending=[]},
 };
}
