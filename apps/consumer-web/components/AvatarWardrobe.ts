import * as T from 'three';
import {mergeGeometries} from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import {normalizeAppearance,type AvatarAppearance} from '../lib/avatarAppearance.ts';

// Original parametric accessories, attached to the existing rig. No remote URLs.
const sphere=new T.SphereGeometry(1,16,10),cube=new T.BoxGeometry(1,1,1),tube=new T.CylinderGeometry(1,1,1,16),ring=new T.TorusGeometry(1,.12,6,20);
for(const g of [sphere,cube,tube,ring])g.userData.shared=true;
export function avatarWardrobe(model:T.Object3D,input:AvatarAppearance,anchors?:{head:T.Object3D;body:T.Object3D}){
 const a=normalizeAppearance(input),owned:T.BufferGeometry[]=[],materials=new Map<string,T.MeshStandardMaterial>(),groups:T.Group[]=[];
 const mat=(c:string)=>{if(!materials.has(c))materials.set(c,new T.MeshStandardMaterial({color:c,roughness:.72}));return materials.get(c)!};
 const part=(parent:T.Object3D,geometry:T.BufferGeometry,color:string,x:number,y:number,z:number,sx:number,sy:number,sz:number)=>{const m=new T.Mesh(geometry,mat(color));m.position.set(x,y,z);m.scale.set(sx,sy,sz);m.castShadow=true;m.userData.wardrobePart=true;parent.add(m);return m};
 const ball=(p:T.Object3D,c:string,x:number,y:number,z:number,w:number,h:number,d:number)=>part(p,sphere,c,x,y,z,w,h,d);
 const block=(p:T.Object3D,c:string,x:number,y:number,z:number,w:number,h:number,d:number)=>part(p,cube,c,x,y,z,w,h,d);
 model.updateMatrixWorld(true);
 const anchor=(name:string,y:number)=>{const g=new T.Group();g.name='wardrobe-'+name;g.position.set(0,y,0);model.add(g);model.updateMatrixWorld(true);const bone=model.getObjectByName(name);if(bone)bone.attach(g);groups.push(g);return g};
 const head=anchors?.head||anchor('head',2.11),body=anchors?.body||anchor('spine01',0);
 if(!anchors)head.position.z+=.08;
 const hair=a.hair!,accent=a.accent!,skin=a.skin!,shirt=a.color!,pants=a.pants!;
 const headwear=a.headwear!,covered=['hijab','turban','kufi','thoppi','beanie'].includes(headwear);
 if(!covered){
  const style=a.style!;if(anchors)ball(head,hair,0,.14,-.025,.14,style==='buzz-cut'?.045:.08,.14);
  if(['long','bob'].includes(style)){for(const side of [-1,1])ball(head,hair,side*.145,style==='bob'?-.04:-.14,-.065,.072,style==='bob'?.15:.27,.13)}
  if(['plait','mullappoo','two-plaits'].includes(style))for(const side of style==='two-plaits'?[-1,1]:[0])for(let i=0;i<7;i++)ball(head,hair,side*.18+Math.sin(i*Math.PI/2)*.018,-.05-i*.062,-.14,.038-i*.002,.043,.04);
  if(style==='mullappoo')for(let i=0;i<11;i++)ball(head,'#fff8df',Math.sin(i*.53)*.13,.08+Math.cos(i*.53)*.07,-.17,.028,.025,.028);
  if(style==='bun')ball(head,hair,0,.17,-.17,.085,.085,.075);
  if(style==='ponytail')for(let i=0;i<5;i++)ball(head,hair,0,.08-i*.065,-.18-i*.018,.058-i*.006,.063,.045);
  if(['curly','afro','spiky'].includes(style))for(let i=0;i<18;i++){const angle=i*2.4,r=Math.sqrt((i+.5)/18)*.18;const x=Math.cos(angle)*r,z=Math.sin(angle)*r-.02;ball(head,hair,x,.14+(1-r/.24)*(style==='afro'?.18:style==='spiky'?.12:.07),z,style==='spiky'?.025:.065,style==='spiky'?.09:.065,.055)}
 }
 if(a.facialHair!=='none'){
  if(['moustache','beard','goatee'].includes(a.facialHair!))for(const side of [-1,1])ball(head,hair,side*.025,-.060,.162,.032,.013,.018);
  if(['beard','goatee','stubble'].includes(a.facialHair!))ball(head,hair,0,-.135,.105,a.facialHair==='goatee'?.042:.12,a.facialHair==='stubble'?.044:.075,.067);
 }
 if(a.glasses!=='none'){
  const shade=['sunglasses','aviators','round-shades'].includes(a.glasses!),round=['round-shades','aviators'].includes(a.glasses!),w=a.glasses==='big-frames'?.064:.047;
  for(const side of [-1,1]){const frame=part(head,round?ring:cube,accent,side*.065,.025,.176,w,round?.044:.037,round?.06:.012);if(!round)ball(head,shade?'#253341':'#b4d6db',side*.065,.025,.184,w*.8,.027,.009);else if(shade)ball(head,'#253341',side*.065,.025,.178,w*.82,.035,.007);block(head,accent,side*.15,.027,.09,.015,.012,.16)}block(head,accent,0,.027,.178,.045,.012,.01);
 }
 for(const side of [-1,1]){
  if(a.earrings==='studs')ball(head,'#e7ba59',side*.177,-.036,.015,.014,.014,.014);
  if(a.earrings==='hoops')part(head,ring,'#e7ba59',side*.18,-.074,.02,.026,.035,.03);
  if(a.earrings==='jhumka'){ball(head,'#e7ba59',side*.18,-.05,.02,.013,.02,.013);part(head,tube,'#e7ba59',side*.18,-.095,.02,.025,.035,.025);for(let i=-1;i<=1;i++)ball(head,'#f2e4bf',side*.18+i*.013,-.117,.025,.007,.008,.007)}
 }
 if(headwear!=='nothing'){
  const cap=['cap','cap-backwards'].includes(headwear),hijab=headwear==='hijab',turban=headwear==='turban';
  ball(head,accent,0,.155,-.01,.185,turban?.15:headwear==='beanie'?.13:.075,.18);
  if(cap){const peak=ball(head,accent,0,.14,headwear==='cap-backwards'?-.17:.17,.17,.02,.13);peak.name='cap-peak'}
  if(['sun-hat','bucket-hat','fedora'].includes(headwear)){part(head,tube,accent,0,.15,0,.27,.025,.25);part(head,tube,accent,0,.22,-.015,headwear==='bucket-hat'?.185:.155,.12,.16);part(head,tube,'#4a3b35',0,.18,-.015,.157,.035,.162)}
  if(['thoppi','kufi'].includes(headwear)){part(head,tube,accent,0,.185,-.01,.17,.085,.16);for(let i=0;i<12;i++)ball(head,'#e4d5ad',Math.sin(i*Math.PI/6)*.17,.185,Math.cos(i*Math.PI/6)*.16-.01,.008,.014,.008)}
  if(turban)for(let i=0;i<5;i++){const wrap=ball(head,accent,0,.12+i*.028,-.02,.19-i*.011,.033,.18-i*.01);wrap.rotation.z=i%2?.12:-.12}
  if(hijab){for(const side of [-1,1])ball(head,accent,side*.15,-.10,-.02,.068,.23,.15);ball(head,accent,0,-.22,-.10,.21,.13,.14)}
 }
 // Garments are original silhouettes; the mapped world and collider never change.
 const garment=(top:number,bottom:number,rTop:number,rBottom:number,color:string)=>{const g=new T.CylinderGeometry(rTop,rBottom,top-bottom,40,10,true);const vertices=g.getAttribute('position');for(let i=0;i<vertices.count;i++){const angle=Math.atan2(vertices.getZ(i),vertices.getX(i)),fold=1+Math.sin(angle*16)*.012;vertices.setX(i,vertices.getX(i)*fold);vertices.setZ(i,vertices.getZ(i)*fold)}g.computeVertexNormals();owned.push(g);const m=part(body,g,color,0,(top+bottom)/2,.065,1,1,.95);m.material.side=T.DoubleSide;return m};
 if(['mundu','lungi','saree','half-saree','abaya','frock'].includes(a.bottom!)){
  garment(a.bottom==='abaya'?1.85:a.bottom==='frock'?1.65:1.25,.20,a.bottom==='abaya'?.32:.31,a.bottom==='frock'?.43:.37,pants);
  garment(.25,.20,.365,.37,accent);if(['mundu','saree','half-saree'].includes(a.bottom!))for(let i=0;i<5;i++)block(body,accent,-.07+i*.033,.70,.405,.009,.83,.012);
  if(['saree','half-saree'].includes(a.bottom!)){
   const vertices:number[]=[],indices:number[]=[],width=a.bottom==='half-saree'?.16:.25;
   for(let j=0;j<=18;j++)for(let i=0;i<=8;i++){const t=j/18,u=i/8-.5;vertices.push(.18-.36*t+u*width,1.22+.66*t+u*width*.5,.32+.025*Math.sin(t*Math.PI)+.007*Math.cos(i*Math.PI));}
   for(let j=0;j<18;j++)for(let i=0;i<8;i++){const k=j*9+i;indices.push(k,k+1,k+10,k,k+10,k+9)}
   const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(vertices,3));geometry.setIndex(indices);geometry.computeVertexNormals();owned.push(geometry);const fabric=new T.Mesh(geometry,mat(pants));fabric.material.side=T.DoubleSide;body.add(fabric);
   const drape=block(body,pants,-.20,1.40,-.24,.20,.86,.025);drape.rotation.z=.06;
  }
 }
 if(a.bottom==='kurti-pants'||a.top==='kurta')garment(1.60,.86,.32,.34,a.bottom==='kurti-pants'?pants:shirt);
 if(a.bottom==='dungarees'){block(body,pants,0,1.49,.32,.37,.49,.055);for(const side of [-1,1])block(body,pants,side*.15,1.79,.29,.055,.39,.04)}
 if(a.bottom==='lungi')for(let i=0;i<6;i++)garment(.34+i*.14,.32+i*.14,.37-i*.007,.37-i*.007,accent);
 if(['jeans','track-pants','churidar'].includes(a.bottom!))for(const side of [-1,1]){const stripe=block(body,a.bottom==='jeans'?'#a4b4bf':accent,side*.22,.68,.07,a.bottom==='churidar'?.018:.026,.85,.018);stripe.name='trouser-detail'}
 if(a.top==='striped-tee')for(let i=0;i<5;i++)block(body,accent,0,1.38+i*.095,.32,.44,.024,.018);
 if(['plain-shirt','collared-shirt','beach-shirt','waistcoat'].includes(a.top!)){for(let i=0;i<5;i++)ball(body,accent,0,1.39+i*.095,.32,.012,.012,.008);if(a.top!=='plain-shirt')for(const side of [-1,1]){const collar=block(body,accent,side*.085,1.82,.28,.07,.09,.025);collar.rotation.z=side*.45}}
 if(a.top==='beach-shirt')for(let i=0;i<7;i++)ball(body,accent,Math.sin(i*2.4)*.19,1.40+(i%4)*.105,.32,.014,.011,.005);
 if(a.top==='sports-tee'){block(body,accent,0,1.67,.32,.18,.17,.02);for(const side of [-1,1])block(body,accent,side*.20,1.6,.29,.035,.46,.02)}
 if(a.top==='hoodie'){ball(body,shirt,0,1.88,-.09,.24,.14,.16);for(const side of [-1,1])block(body,accent,side*.08,1.76,.31,.009,.23,.009)}
 if(a.top==='jacket'){for(const side of [-1,1]){block(body,shirt,side*.15,1.55,.32,.22,.53,.065);block(body,accent,side*.20,1.45,.36,.12,.02,.025)}}
 if(a.top==='waistcoat')for(const side of [-1,1]){const lapel=block(body,accent,side*.105,1.70,.32,.055,.31,.025);lapel.rotation.z=side*.3}
 if(a.carry!=='nothing'){
  if(a.carry==='backpack'){ball(body,accent,0,1.55,-.25,.25,.32,.13);for(const side of [-1,1])block(body,accent,side*.20,1.62,.16,.035,.47,.025)}
  if(a.carry==='sling-bag'){const strap=block(body,accent,0,1.56,.23,.025,.70,.025);strap.rotation.z=-.60;ball(body,accent,.28,1.23,.08,.16,.19,.08)}
  if(a.carry==='tote-bag'){block(body,accent,.40,1.08,.02,.24,.33,.12);part(body,ring,accent,.40,1.34,.02,.09,.12,.08)}
  if(a.carry==='camera'){part(body,ring,'#403b36',0,1.72,.20,.14,.23,.07);block(body,'#263443',0,1.48,.28,.24,.16,.10);const lens=part(body,tube,'#172131',0,1.48,.36,.065,.10,.065);lens.rotation.x=Math.PI/2;ball(body,'#5f97ae',0,1.48,.415,.05,.05,.007)}
 }
 // Combine static accessory pieces per bone/material; skeletal anchors keep animation.
 for(const parent of [head,body]){
  const buckets=new Map<T.Material,T.Mesh[]>();for(const child of parent.children)if(child instanceof T.Mesh&&child.userData.wardrobePart&&!Array.isArray(child.material)){const list=buckets.get(child.material)||[];list.push(child);buckets.set(child.material,list)}
  for(const [material,meshes] of buckets){if(meshes.length<2)continue;const geometries=meshes.map(m=>{m.updateMatrix();const g=m.geometry.clone();g.applyMatrix4(m.matrix);if(!g.index)return g;const flat=g.toNonIndexed();g.dispose();return flat});const merged=mergeGeometries(geometries,false);geometries.forEach(g=>g.dispose());if(!merged)continue;owned.push(merged);const mesh=new T.Mesh(merged,material);mesh.castShadow=true;parent.add(mesh);meshes.forEach(m=>m.removeFromParent());}
 }
 return {dispose(){groups.forEach(g=>g.removeFromParent());owned.forEach(g=>g.dispose());materials.forEach(m=>m.dispose())},groups};
}
