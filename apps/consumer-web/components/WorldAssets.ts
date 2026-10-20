import * as T from 'three';
import {Locomotion} from '../lib/locomotion.ts';
export type Appearance={color?:string;skin?:string;hair?:string;style?:string;pants?:string};
const mats=new Map<string,T.MeshStandardMaterial>();
export function material(color:string){if(!mats.has(color))mats.set(color,new T.MeshStandardMaterial({color,roughness:['#243b77','#485589','#2b4964'].includes(color)?.3:.74,metalness:['#243b77','#485589','#2b4964'].includes(color)?.3:0}));return mats.get(color)!;}
export function mesh(g:T.BufferGeometry,color:string,parent:T.Object3D,x=0,y=0,z=0){const m=new T.Mesh(g,material(color));m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;}
const cube=new T.BoxGeometry(1,1,1),sphere=new T.SphereGeometry(1,12,8),cylinder=new T.CylinderGeometry(1,1,1,8);
for(const g of [cube,sphere,cylinder])g.userData.shared=true;
export function box(p:T.Object3D,c:string,x:number,y:number,z:number,w:number,h:number,d:number){const m=mesh(cube,c,p,x,y,z);m.scale.set(w,h,d);return m;}
export function oval(p:T.Object3D,c:string,x:number,y:number,z:number,w:number,h:number,d:number){const m=mesh(sphere,c,p,x,y,z);m.scale.set(w,h,d);return m;}
const limbGeometry=new T.CapsuleGeometry(1,1,4,8);limbGeometry.userData.shared=true;
function limb(p:T.Object3D,c:string,x:number,y:number,z:number,w:number,h:number,d:number){const m=mesh(limbGeometry,c,p,x,y,z);m.scale.set(w,h/3,d);return m;}
export function human(a:Appearance={},calibrated=false){
 const root=new T.Group(),body=new T.Group(),details=new T.Group(),far=new T.Group();root.add(body,far);body.add(details);far.visible=false;
 const skin=a.skin||'#bf855e',hair=a.hair||'#302821',shirt=a.color||'#ed945d',pants=a.pants||'#29485d';
 // Adult proportions: tapered torso, articulated limbs and a smaller shaped head.
 oval(body,shirt,0,1.57,0,.31,.42,.195);oval(details,shirt,0,1.89,-.09,.22,.12,.15);box(details,'#e6dccc',0,1.7,.192,.017,.4,.013);box(details,shirt,0,1.37,.185,.30,.12,.04);oval(body,pants,0,1.18,0,.245,.16,.165);
 limb(body,skin,0,1.99,0,.082,.18,.077);const head=new T.Group();head.position.set(0,2.16,.015);body.add(head);
 oval(head,skin,0,0,0,.163,.205,.157);oval(head,skin,0,-.10,.035,.125,.09,.125);oval(head,hair,0,.14,-.022,.17,.10,.16);
 if(a.style==='long'){oval(head,hair,-.14,-.025,-.05,.065,.22,.13);oval(head,hair,.14,-.025,-.05,.065,.22,.13)}
 if(a.style==='cap'){oval(head,shirt,0,.175,0,.18,.06,.17);oval(head,shirt,0,.16,.15,.16,.018,.12)}
 const face=new T.Group();head.add(face);for(const side of [-1,1]){oval(face,'#f3eee3',side*.06,.025,.143,.033,.018,.014);oval(face,'#283336',side*.06,.025,.155,.012,.013,.007);oval(face,hair,side*.06,.065,.143,.038,.009,.012);oval(face,skin,side*.162,0,0,.025,.047,.03)}oval(face,skin,0,-.015,.16,.026,.045,.035);oval(face,'#985e51',0,-.10,.14,.048,.008,.008);
 for(const side of [-1,1]){limb(details,'#e3decf',side*.15,1.82,.151,.035,.23,.015)}
 const legs:T.Group[]=[],knees:T.Group[]=[],arms:T.Group[]=[],elbows:T.Group[]=[];
 for(const side of [-1,1]){const leg=new T.Group();leg.position.set(side*.135,1.15,0);body.add(leg);limb(leg,pants,0,-.25,0,.11,.52,.115);const knee=new T.Group();knee.position.y=-.48;leg.add(knee);limb(knee,pants,0,-.22,0,.085,.48,.09);oval(knee,'#f3f1e6',0,-.59,.055,.115,.035,.205);oval(knee,'#36495b',0,-.54,.055,.108,.055,.19);legs.push(leg);knees.push(knee);
 const arm=new T.Group();arm.position.set(side*.34,1.86,0);arm.rotation.z=side*.10;body.add(arm);limb(arm,shirt,0,-.19,0,.093,.38,.09);const elbow=new T.Group();elbow.position.y=-.35;arm.add(elbow);limb(elbow,skin,0,-.15,.008,.064,.34,.062);oval(elbow,skin,0,-.37,.018,.065,.10,.04);arms.push(arm);elbows.push(elbow);}
 // Low-detail silhouette shares cached geometries/materials.
 oval(far,shirt,0,1.55,0,.30,.43,.17);oval(far,skin,0,2.16,0,.16,.20,.15);for(const side of [-1,1])limb(far,pants,side*.135,.6,0,.10,1.15,.10);
 let detail=true;root.userData.setLOD=(distance:number)=>{detail=distance<35;face.visible=detail;details.visible=detail;body.visible=distance<75;far.visible=distance>=75};
 const gait=new Locomotion();
 root.userData.animate=(t:number,speed:number,mode?:string)=>{
  const {phase,run,weight,dt}=gait.update(t,speed,mode,calibrated),step=Math.sin(phase)*(.5+run*.27)*weight;
  const ease=1-Math.exp(-dt*24);
  // Relax residual seated/cycling poses into the gait, including shoulder roll.
  for(let i=0;i<2;i++){
   const phaseSide=phase+i*Math.PI,target=i?-step:step;
   legs[i].rotation.x+=(target-legs[i].rotation.x)*ease;
   const knee=(Math.max(0,-Math.sin(phaseSide))*(.45+run*1.1)+run*.12)*weight;
   knees[i].rotation.x+=(knee-knees[i].rotation.x)*ease;
   arms[i].rotation.x+=(-target*(.65+run*.45)-arms[i].rotation.x)*ease;
   elbows[i].rotation.x+=(-.13-run*.9-elbows[i].rotation.x)*ease;
   arms[i].rotation.z+=((i?1:-1)*(.10+run*.05)-arms[i].rotation.z)*ease;
  }
  const bounce=Math.abs(Math.sin(phase))*(.026+run*.055)*weight+Math.sin(t*1.8)*.009*(1-weight);
  body.position.y+=(bounce-body.position.y)*ease;body.position.z+=(0-body.position.z)*ease;
  body.rotation.z=Math.sin(phase)*(.018+run*.014)*weight;
  body.rotation.y=Math.sin(phase)*.025*weight;
  body.rotation.x+=((root.userData.emote==='collect'?.25:run*.15*weight)-body.rotation.x)*ease;
  head.rotation.y=detail&&weight<.1?Math.sin(t*.7)*.035:0;
  head.rotation.x=root.userData.speaking?Math.sin(t*7)*.035:-run*.06;
  if(root.userData.emote==='wave'){arms[1].rotation.z=-2.1+Math.sin(t*8)*.15;elbows[1].rotation.x=-.5}
 };

 root.userData.sit=()=>{legs.forEach(l=>l.rotation.x=-1.3);knees.forEach(k=>k.rotation.x=1.3);arms.forEach(a=>a.rotation.x=-.3);body.position.y=-.35};root.userData.cycle=(t:number,speed:number)=>{const pedal=Math.sin(t*8)*Math.min(.25,Math.max(0,speed)*.05);legs[0].rotation.x=-.7+pedal;legs[1].rotation.x=-.7-pedal;arms.forEach(a=>a.rotation.x=-.8);knees.forEach(k=>k.rotation.x=.9);body.position.y=-.22;body.position.z=-.2};root.userData.swim=(t:number)=>{body.rotation.x=-Math.PI/2;body.position.y=-.1;arms.forEach((a,i)=>{a.rotation.x=t*3+i*Math.PI;a.rotation.z=(i?1:-1)*.3});legs.forEach((l,i)=>l.rotation.x=Math.sin(t*5+i*Math.PI)*.2)};return root;
}
export function tree(parent:T.Object3D,x:number,z:number,seed:number){
 const g=new T.Group();g.position.set(x,0,z);parent.add(g);
 mesh(new T.CylinderGeometry(.12,.26,4.3,7),'#79634f',g,0,2.1,0);
 for(let i=0;i<5;i++){const angle=i*2.4+seed,branch=mesh(new T.CylinderGeometry(.045,.09,1.5,5),'#79634f',g,Math.sin(angle)*.42,3.25+i*.2,Math.cos(angle)*.42);branch.rotation.z=Math.cos(angle)*.45;branch.rotation.x=Math.sin(angle)*.45;const crown=oval(g,['#437958','#5a8b5d','#709965'][(seed+i)%3],Math.sin(angle)*.75,4.0+i*.25,Math.cos(angle)*.75,1.5,1.45,1.45);crown.rotation.y=angle;}
 return g;
}
export function fruit(kind:string,index:number){const g=new T.Group();if(kind==='treasure'){box(g,'#95542f',0,.4,0,1.15,.7,.8);const lid=mesh(new T.CylinderGeometry(.55,.55,1.15,8,1,false,0,Math.PI),'#b7743d',g,0,.7,0);lid.rotation.z=Math.PI/2;for(const x of [-.43,.43])box(g,'#efc464',x,.48,0,.12,.9,.84);box(g,'#ffe397',0,.55,.45,.23,.25,.09);}else if(kind==='gem'){const colors=['#64c7b2','#e57483','#79b6e1','#cab1fa'];const m=mesh(new T.OctahedronGeometry(.72,0),colors[index%4],g,0,.55,0);m.scale.y=1.5;const ring=mesh(new T.TorusGeometry(1,.025,4,24),'#ffe3a5',g,0,-.15,0);ring.rotation.x=Math.PI/2;}else{switch(index%5){case 0:oval(g,'#dd5c4e',-.16,.35,0,.38,.45,.38);oval(g,'#ee7151',.16,.35,0,.38,.45,.38);break;case 1:oval(g,'#f5a53b',0,.38,0,.5,.48,.5);break;case 2:for(let i=0;i<3;i++){const b=mesh(new T.TorusGeometry(.45,.13,6,10,2.2),'#f4d65b',g,(i-1)*.17,.5,0);b.rotation.z=-.8;}break;case 3:mesh(new T.ConeGeometry(.48,.95,9),'#e35d66',g,0,.45,0).rotation.z=Math.PI;for(let i=0;i<10;i++)oval(g,'#ffe3a0',Math.sin(i*2)*.31,.25+(i%3)*.16,Math.cos(i*2)*.31,.035,.05,.035);break;default:oval(g,'#e6b650',0,.5,0,.38,.65,.38);for(let i=0;i<5;i++){const l=mesh(new T.ConeGeometry(.12,.7,4),'#529064',g,Math.sin(i)*.15,1.25,Math.cos(i)*.15);l.rotation.z=Math.sin(i)*.4;}}box(g,'#73533d',0,.91,0,.065,.25,.065);const leaf=oval(g,'#589569',.16,.95,0,.25,.055,.1);leaf.rotation.z=.35;}return g;}
export function bench(p:T.Object3D,x:number,z:number,angle=0){const g=new T.Group();g.position.set(x,.1,z);g.rotation.y=angle;p.add(g);for(let i=0;i<3;i++){box(g,'#bc9366',0,.55,i*.16,2,.1,.13);box(g,'#bc9366',0,.95+i*.17,-.06,2,.12,.08);}for(const s of [-.7,.7])box(g,'#415e55',s,.3,.2,.12,.6,.5);}
const tireGeometry=new T.CylinderGeometry(.37,.37,.23,18),rimGeometry=new T.CylinderGeometry(.255,.255,.245,12);
for(const g of [tireGeometry,rimGeometry])g.userData.shared=true;
const vehicleMaterials=new Map<string,T.MeshStandardMaterial>();
function finish(color:string,metalness=.45,roughness=.27){const key=color+metalness+roughness;if(!vehicleMaterials.has(key))vehicleMaterials.set(key,new T.MeshStandardMaterial({color,metalness,roughness}));return vehicleMaterials.get(key)!}
function coachwork(p:T.Object3D,color:string,rings:number[][]){
 const positions:number[]=[],indices:number[]=[];
 // z, half-width, lower edge, shoulder/roof height.
 for(const [z,w,lo,hi] of rings)positions.push(-w,lo,z,w,lo,z,w,hi,z,-w,hi,z);
 for(let n=0;n<rings.length-1;n++)for(let i=0;i<4;i++){const a=n*4+i,b=n*4+(i+1)%4,c=b+4,d=a+4;indices.push(a,b,d,b,c,d)}
 indices.push(0,3,2,0,2,1);const k=(rings.length-1)*4;indices.push(k,k+1,k+2,k,k+2,k+3);
 const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(positions,3));g.setIndex(indices);g.setAttribute('uv',new T.Float32BufferAttribute(new Array(positions.length/3*2).fill(0),2));g.computeVertexNormals();
 const m=new T.Mesh(g,finish(color));m.castShadow=true;m.receiveShadow=true;p.add(m);return m;
}
export function car(p:T.Object3D,x:number,z:number,angle:number,color:string){
 const g=new T.Group();g.position.set(x,.03,z);g.rotation.y=angle;p.add(g);
 coachwork(g,color,[[-2.06,.72,.5,.73],[-1.7,.93,.46,.96],[-.8,.96,.44,1],[.9,.96,.44,.9],[1.85,.86,.45,.72],[2.06,.73,.51,.66]]);
 const cabin=coachwork(g,'#233e53',[[-1.15,.73,.94,1.01],[-.55,.69,.95,1.52],[.47,.67,.93,1.48],[1.13,.78,.86,.94]]);cabin.name='vehicle-glazing';
 const roof=box(g,color,0,1.51,-.04,1.38,.075,1.04);roof.material=finish(color);
 for(const side of [-1,1]){
  const sill=box(g,'#49cfe2',side*.935,.48,0,.045,.065,2.9);sill.material=finish('#49cfe2',.6,.24);
  box(g,color,side*.72,1.24,-.08,.05,.52,.07);
  const mirror=oval(g,color,side*1.0,1.12,.65,.16,.08,.12);mirror.material=finish(color);
  box(g,'#b5cdd8',side*.955,.89,-.12,.018,.035,.23);
  for(const axle of [-1.25,1.28]){const tire=mesh(tireGeometry,'#17202c',g,side*.91,.4,axle);tire.rotation.z=Math.PI/2;const rim=mesh(rimGeometry,'#a6b7c4',g,side*.925,.4,axle);rim.material=finish('#a6b7c4',.85,.24);rim.rotation.z=Math.PI/2;}
  box(g,'#defaff',side*.52,.72,1.96,.5,.075,.04);box(g,'#f87189',side*.5,.82,-1.98,.52,.065,.04);
 }
 box(g,'#14222e',0,.57,2.04,.91,.14,.04);box(g,'#14222e',0,.53,-2.07,1.22,.11,.03);
 box(g,'#e6eee9',0,.67,-2.076,.43,.12,.02);return g;
}
export function motorbike(p:T.Object3D,x=0,z=0){
 const g=new T.Group();g.position.set(x,0,z);p.add(g);
 for(const z of [-.83,.88]){const w=mesh(new T.CylinderGeometry(.42,.42,.19,18),'#19212b',g,0,.44,z);w.rotation.z=Math.PI/2;const rim=mesh(new T.CylinderGeometry(.3,.3,.20,14),'#64cfe2',g,0,.44,z);rim.rotation.z=Math.PI/2;}
 oval(g,'#243b55',0,.9,.16,.29,.27,.51);box(g,'#13202e',0,.73,-.36,.4,.17,.8);box(g,'#394c60',0,.65,0,.4,.36,.43);
 for(const side of [-1,1]){const fork=box(g,'#a9bccb',side*.13,.81,.66,.065,.88,.07);fork.rotation.x=-.22;box(g,'#55d5e6',side*.29,.91,.16,.03,.07,.65);}
 box(g,'#233748',0,1.31,.52,.75,.07,.1);oval(g,'#b8eeff',0,1.08,.72,.16,.13,.04);box(g,'#eb7998',0,.82,-.86,.25,.06,.03);return g;
}
export function bicycle(p:T.Object3D,x=0,z=0){const g=new T.Group();g.position.set(x,0,z);p.add(g);for(const z of [-.8,.8]){const w=mesh(new T.TorusGeometry(.48,.065,6,18),'#253c51',g,0,.5,z);w.rotation.y=Math.PI/2;}const bar=(a:number[],b:number[])=>{const aa=new T.Vector3(a[0],a[1],a[2]),bb=new T.Vector3(b[0],b[1],b[2]),m=mesh(new T.CylinderGeometry(.045,.045,aa.distanceTo(bb),6),'#51bed1',g);m.position.copy(aa).add(bb).multiplyScalar(.5);m.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),bb.sub(aa).normalize())};for(const [a,b] of [[[0,.5,-.8],[0,1.05,-.25]],[[0,1.05,-.25],[0,.5,0]],[[0,.5,0],[0,.5,-.8]],[[0,1.05,-.25],[0,1.1,.5]],[[0,1.1,.5],[0,.5,0]],[[0,1.1,.5],[0,.5,.8]]])bar(a,b);box(g,'#263849',0,1.12,-.2,.3,.12,.42);box(g,'#344d60',0,.79,.09,.18,.34,.39);box(g,'#c9f7fc',0,1.19,.67,.13,.12,.08);box(g,'#273e4d',0,1.32,.55,.7,.07,.09);return g;}

export function streetSign(parent:T.Object3D,name:string,x:number,z:number,angle:number){
 const g=new T.Group();g.position.set(x,0,z);g.rotation.y=angle;parent.add(g);
 const width=Math.max(3.4,Math.min(7,name.length*.22));for(const s of [-1,1])box(g,'#182735',s*(width/2-.12),.85,0,.09,1.7,.09);
 box(g,'#152532',0,1.55,0,width,1.05,.12);
 const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=160;const c=canvas.getContext('2d')!;
 c.fillStyle='#132b42';c.fillRect(0,0,1024,160);c.strokeStyle='#83a8bc';c.lineWidth=7;c.strokeRect(12,12,1000,136);c.fillStyle='#edf6ff';c.font='bold 70px Arial';c.textAlign='center';c.textBaseline='middle';c.fillText(name,512,83,950);
 const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;const face=new T.Mesh(new T.PlaneGeometry(width-.1,.92),new T.MeshBasicMaterial({map:texture}));face.position.set(0,1.55,.067);g.add(face);const back=face.clone();back.position.z=-.067;back.rotation.y=Math.PI;g.add(back);return g;
}
