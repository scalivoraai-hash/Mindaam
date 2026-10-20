import * as T from 'three';
import {box,mesh,material} from './WorldAssets';

import {BRAND} from '@/lib/brand';
let approvedMark:HTMLImageElement|undefined;
const waiting=new Map<HTMLCanvasElement,()=>void>();
function brandImage(){
 if(!approvedMark&&typeof Image!=='undefined'){approvedMark=new Image();approvedMark.onload=()=>{for(const draw of waiting.values())draw();waiting.clear();window.dispatchEvent(new Event('mindaam-brand-ready'))};approvedMark.src=BRAND.mark}
 return approvedMark;
}
export function brandOnCanvas(c:CanvasRenderingContext2D,x:number,y:number,size=42){
 const im=brandImage();const draw=()=>{if(im?.complete&&im.naturalWidth)c.drawImage(im,x,y,size,size*93/108)};
 if(im?.complete)draw();else waiting.set(c.canvas,draw);
}
/** Refresh late-loaded approved artwork exactly once, and remove listeners on disposal. */
export function brandTexture(texture:T.Texture){const refresh=()=>{texture.needsUpdate=true};window.addEventListener('mindaam-brand-ready',refresh,{once:true});texture.addEventListener('dispose',()=>{window.removeEventListener('mindaam-brand-ready',refresh);waiting.delete(texture.image) });return texture}

export function billboardCanvas(headline?:string){
  const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=576;const c=canvas.getContext('2d')!;
  const bg=c.createLinearGradient(0,0,1024,576);bg.addColorStop(0,'#092b59');bg.addColorStop(.55,'#192459');bg.addColorStop(1,'#591772');c.fillStyle=bg;c.fillRect(0,0,1024,576);
  const glow=c.createRadialGradient(810,250,10,810,250,360);glow.addColorStop(0,'#50dbe34d');glow.addColorStop(1,'#5e56d900');c.fillStyle=glow;c.fillRect(0,0,1024,576);
  c.strokeStyle='#76bde529';c.lineWidth=1;for(let y=400;y<576;y+=28){c.beginPath();c.moveTo(0,y);c.lineTo(1024,y);c.stroke()}
  // Original city illustration; no fabricated advertiser, reach or attendance claims.
  for(let i=0;i<10;i++){const x=660+i*35,h=80+(i*47)%160;c.fillStyle=i%2?'#6ac2d62a':'#8490d92f';c.fillRect(x,454-h,30,h);c.fillStyle='#b0e9ff55';for(let yy=460-h;yy<445;yy+=17)for(let xx=x+7;xx<x+27;xx+=10)c.fillRect(xx,yy,3,6)}
  brandOnCanvas(c,60,49,45);c.fillStyle='#fff';c.font='bold 36px sans-serif';c.fillText('Mindaam',126,87);
  c.font='600 15px sans-serif';c.fillStyle='#a9d7ed';c.fillText('PEOPLE  ·  PLACES  ·  POSSIBILITIES',60,142);
  const lines=headline?wrap(c,headline,820,58):['YOUR BRAND','BELONGS HERE.'];
  c.font='800 68px sans-serif';lines.slice(0,3).forEach((line,i)=>{c.fillStyle=i===1?'#72f0e6':'#fff';c.fillText(line,60,243+i*76,890)});
  c.font='25px sans-serif';c.fillStyle='#d1e6f9';c.fillText('Connect with explorers in a living world.',60,414,875);
  const button=c.createLinearGradient(60,0,470,0);button.addColorStop(0,'#b9f678');button.addColorStop(1,'#57e2de');c.fillStyle=button;c.beginPath();c.roundRect(60,452,410,69,16);c.fill();c.fillStyle='#123345';c.font='bold 25px sans-serif';c.fillText('ADVERTISE NOW   ↗',87,496);
  c.font='16px sans-serif';c.fillStyle='#d8e6fb';c.fillText('EXPLORE. MEET. GROW.',669,500);return canvas;
}
function wrap(c:CanvasRenderingContext2D,text:string,width:number,size:number){c.font=`bold ${size}px sans-serif`;const lines:string[]=[];let line='';for(const word of text.split(/\s+/)){if(c.measureText(line+' '+word).width>width&&line){lines.push(line);line=word}else line+=(line?' ':'')+word}if(line)lines.push(line);return lines}

/** Separate outward-facing copies prevent mirrored text when a board is approached from behind. */
export function twoSidedPanel(parent:T.Group,texture:T.Texture,width:number,height:number,x:number,y:number,z:number,depth=.04){
  const mat=new T.MeshBasicMaterial({map:texture,toneMapped:false});mat.userData.cityOwned=true;
  const front=new T.Mesh(new T.PlaneGeometry(width,height),mat);front.position.set(x,y,z);parent.add(front);
  const back=new T.Mesh(front.geometry,mat);back.position.set(x,y,z-depth);back.rotation.y=Math.PI;parent.add(back);
  return front;
}

export function premiumBus(number:string,destination:string,open=false,upper=false){
  const g=new T.Group(),navy='#243b77',trim='#58d5e0',glass='#2b4964';
  box(g,'#152335',0,.64,0,2.48,.5,7);box(g,navy,0,1.24,0,2.48,.74,7);
  for(const x of [-1.22,1.22]){
    box(g,trim,x,1.18,0,.03,.07,6.85);box(g,'#7873d2',x,1.45,-.8,.035,.17,4.8);
    for(const z of [-2.15,2.12]){const w=mesh(new T.CylinderGeometry(.5,.5,.23,18),'#15212e',g,x,.5,z);w.rotation.z=Math.PI/2;const rim=mesh(new T.CylinderGeometry(.32,.32,.25,12),'#a9bbc7',g,x,.5,z);rim.rotation.z=Math.PI/2}
    for(let z=-2.6;z<3;z+=1.18){box(g,navy,x,2.48,z-.52,.08,1.85,.1);const m=box(g,glass,x,2.52,z,.025,1.56,1.05);if(open){const glassMat=new T.MeshStandardMaterial({color:'#b0d7e4',transparent:true,opacity:.12,roughness:.19,depthWrite:false});glassMat.userData.cityOwned=true;m.material=glassMat}}
  }
  box(g,navy,0,2.42,-3.47,2.48,2.06,.12);box(g,navy,0,1.46,3.48,2.48,.6,.12);
  const wind=box(g,glass,0,2.42,3.49,2.27,1.45,.05);if(open){const m=new T.MeshStandardMaterial({color:'#b0d7e4',transparent:true,opacity:.12,roughness:.2,depthWrite:false});m.userData.cityOwned=true;wind.material=m}
  if(!open){box(g,navy,0,3.4,0,2.5,.18,7);box(g,navy,0,4.26,0,2.48,1.65,7);for(const side of [-1,1])for(let z=-2.6;z<3;z+=1.18)box(g,glass,side*1.25,4.28,z,.03,1.13,1.03);box(g,glass,0,4.28,3.515,2.22,1.12,.03);box(g,'#485589',0,5.13,0,2.52,.15,7.02)}
  else {box(g,'#293f55',0,upper?3.42:.94,0,2.35,.10,6.7);const seats=new T.Group();seats.position.y=upper?2.5:0;g.add(seats);for(const x of [-.73,.73])for(let z=-2.5;z<=2.5;z+=.55){box(seats,'#435488',x,1.3,z,.55,.18,.5);box(seats,'#435488',x,1.64,z-.25,.55,.7,.1)}}
  for(const x of [-.9,.9]){box(g,'#e3faff',x,1.16,3.56,.38,.10,.03);box(g,'#fb8099',x,1.1,-3.54,.25,.12,.03);box(g,'#243b55',x*1.53,2.4,3.05,.15,.35,.12)}
  box(g,'#13273b',0,.76,3.55,1.5,.22,.03);
  const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=256;const c=canvas.getContext('2d')!;c.fillStyle='#0b182c';c.fillRect(0,0,1024,256);c.fillStyle='#f7e5a5';c.font='bold 87px sans-serif';c.fillText(number+'  '+destination,40,157,940);
  const texture=brandTexture(new T.CanvasTexture(canvas));texture.colorSpace=T.SRGBColorSpace;twoSidedPanel(g,texture,2.22,.47,0,3.1,3.58,7.16);
  const sideCanvas=document.createElement('canvas');sideCanvas.width=1024;sideCanvas.height=256;const sc=sideCanvas.getContext('2d')!;sc.fillStyle=navy;sc.fillRect(0,0,1024,256);brandOnCanvas(sc,75,70,95);sc.fillStyle='#f0f7ff';sc.font='bold 86px sans-serif';sc.fillText('Mindaam',220,161,740);
  const sideTex=brandTexture(new T.CanvasTexture(sideCanvas));sideTex.colorSpace=T.SRGBColorSpace;
  for(const side of [-1,1]){const m=new T.Mesh(new T.PlaneGeometry(4.8,.87),new T.MeshBasicMaterial({map:sideTex,toneMapped:false}));m.position.set(side*1.269,1.82,-.25);m.rotation.y=side*Math.PI/2;g.add(m)}
  return g;
}

export function stageDetails(g:T.Group){
  box(g,'#13213a',0,.38,-10,17,.76,7);box(g,'#75dfeb',0,.79,-6.51,17,.055,.06);
  for(const x of [-8.3,8.3]){box(g,'#18263f',x,3.6,-10,.22,6.1,6.7);box(g,'#aa81e7',x-.12*Math.sign(x),3.2,-12.8,.1,5.5,.1);box(g,'#68dbea',x-.12*Math.sign(x),3.2,-7,.1,5.5,.1);for(let i=0;i<3;i++){box(g,'#151d2b',x,1.1+i*.8,-7.5,.65,.7,.65)}}
  box(g,'#273651',0,6.4,-9,17,.18,.22);
  for(let x=-7;x<=7;x+=2){box(g,'#131f32',x,6.05,-9,.3,.5,.4);box(g,x%4?'#b595ef':'#79dbeb',x,5.78,-8.98,.2,.025,.25)}
  const canvas=billboardCanvas('LIVE TOGETHER.');const c=canvas.getContext('2d')!;c.fillStyle='#122348';c.fillRect(45,370,910,180);c.fillStyle='#c8ddf5';c.font='27px sans-serif';c.fillText('Music. Conversations. Shared moments.',60,422);c.font='bold 21px sans-serif';c.fillStyle='#9ce7ed';c.fillText('MINDAAM LIVE',60,487);
  const texture=brandTexture(new T.CanvasTexture(canvas));texture.colorSpace=T.SRGBColorSpace;const screen=twoSidedPanel(g,texture,11.4,6.4125,0,4.1,-13.15);screen.userData.eventVideoSurface=true;screen.userData.cityAction=()=>window.dispatchEvent(new CustomEvent('pulse-stage-view'));
  box(g,'#101b2b',0,4.1,-13.28,11.8,6.75,.15);
  for(const x of [-5.85,5.85])box(g,'#71cada',x,4.1,-13.12,.045,6.5,.04);
  // Reused acoustic panels, open ceiling ribs and two shadow-free stage lights.
  // No reflective render targets or additional shadow maps on mobile.
  for(const z of [-11,-4,3,10]){box(g,'#34445c',0,7.75,z,21.8,.23,.42);box(g,'#1c2940',0,7.5,z,21.5,.08,.08)}
  for(const side of [-1,1]){
    for(let z=-10;z<13;z+=2.5){box(g,'#384358',side*10.82,3.7,z,.12,5.2,1.95);box(g,z%2?'#5b80af':'#796698',side*10.73,4.1,z-1,.04,4.6,.05)}
    box(g,'#b09978',side*10.7,.85,0,.18,1.5,25);
    const fixture=new T.SpotLight(side<0?'#8f89ee':'#6fd4e1',85,24,.6,.65,1.5);fixture.position.set(side*7,5.76,-9);fixture.target.position.set(side*3,.6,-10);g.add(fixture,fixture.target);
    const beam=new T.Mesh(new T.ConeGeometry(2.15,1,16,1,true),new T.ShaderMaterial({uniforms:{beamColour:{value:fixture.color.clone()},strength:{value:.1}},vertexShader:'varying vec2 beamUv; void main(){beamUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',fragmentShader:'uniform vec3 beamColour; uniform float strength; varying vec2 beamUv; void main(){float edge=pow(sin(beamUv.x*3.14159265),2.0);float fade=smoothstep(0.0,0.2,beamUv.y)*mix(0.3,1.0,beamUv.y);gl_FragColor=vec4(beamColour,strength*edge*fade);}',transparent:true,depthWrite:false,side:T.DoubleSide,blending:T.AdditiveBlending}));beam.userData.stageBeam=fixture;beam.renderOrder=1;g.add(beam);
    const led=new T.Mesh(new T.CircleGeometry(.23,12),new T.MeshBasicMaterial({color:fixture.color}));led.userData.stageLed=fixture;g.add(led);
    box(g,'#152239',side*9.25,3.8,-11,1.65,3.8,.15);box(g,'#697fb2',side*9.25,3.8,-10.9,1.48,3.55,.03);
    box(g,'#c2b391',side*9.25,2.1,-10.85,1.45,.08,.04);
  }
  // Rounded upholstery and armrests share two instanced draws across all 36 seats.
  const rounded=new T.BoxGeometry(1,1,1,3,3,3),positions=rounded.attributes.position,normals=rounded.attributes.normal,v=new T.Vector3(),core=new T.Vector3();
  for(let i=0;i<positions.count;i++){v.fromBufferAttribute(positions,i);core.copy(v).clampScalar(-.38,.38);v.sub(core).normalize();normals.setXYZ(i,v.x,v.y,v.z);v.multiplyScalar(.12).add(core);positions.setXYZ(i,v.x,v.y,v.z)}
  rounded.computeBoundingSphere();
  const cushions=new T.InstancedMesh(rounded,material('#555879'),72),frames=new T.InstancedMesh(rounded,material('#29384c'),108),seatTransform=new T.Object3D();let cushion=0,frame=0;
  const place=(mesh:T.InstancedMesh,index:number,x:number,y:number,z:number,w:number,h:number,d:number,tilt=0)=>{seatTransform.position.set(x,y,z);seatTransform.scale.set(w,h,d);seatTransform.rotation.set(tilt,0,0);seatTransform.updateMatrix();mesh.setMatrixAt(index,seatTransform.matrix)};
  for(let row=0;row<6;row++)for(const x of [-7,-5.4,-3.8,3.8,5.4,7]){const z=-3+row*2.1;place(cushions,cushion++,x,.65,z,1.1,.3,1.02);place(cushions,cushion++,x,1.13,z+.42,1.1,1.08,.28,-.12);for(const side of [-.62,.62])place(frames,frame++,x+side,.88,z,.14,.2,1.08);place(frames,frame++,x,.28,z,.55,.5,.62)}
  cushions.receiveShadow=true;frames.receiveShadow=true;g.add(cushions,frames);
  for(const x of [-2.4,2.4])for(let z=-4;z<12;z+=2)box(g,'#b5a1f1',x,.1,z,.05,.03,.8);
}
