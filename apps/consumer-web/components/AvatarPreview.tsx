'use client';
import {useEffect,useRef,useState} from 'react';
import * as T from 'three';
import {human,type Appearance} from './WorldAssets';
export default function AvatarPreview({appearance}:{appearance:Appearance}){
 const host=useRef<HTMLDivElement>(null),turn=useRef(.12),zoom=useRef(4.5),[fallback,setFallback]=useState(false);
 const latest=useRef(appearance);latest.current=appearance;
 useEffect(()=>{
  const element=host.current;if(!element)return;let renderer:T.WebGLRenderer;
  try{renderer=new T.WebGLRenderer({antialias:true,alpha:true})}catch{setFallback(true);return}
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.25));renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;element.append(renderer.domElement);
  const scene=new T.Scene(),camera=new T.PerspectiveCamera(34,1,.1,20);
  scene.add(new T.HemisphereLight('#f0f7ff','#655444',2.1));const key=new T.DirectionalLight('#fff1df',2.7);key.position.set(3,4,4);scene.add(key);const fill=new T.DirectionalLight('#8acfff',1.2);fill.position.set(-3,2,-1);scene.add(fill);
  let factory:Awaited<ReturnType<typeof import('./loadCinematicCharacter').loadCinematicCharacter>>|null=null,avatar:T.Group|null=null,seen='',closed=false,frame=0,last=0;
  import('./loadCinematicCharacter').then(m=>m.loadCinematicCharacter()).then(f=>{if(closed)f.dispose();else{factory=f;seen=''}}).catch(()=>setFallback(true));
  const resize=()=>{const w=Math.max(1,element.clientWidth),h=Math.max(1,element.clientHeight);renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()};const observer=new ResizeObserver(resize);observer.observe(element);resize();
  let drag:number|null=null;const down=(e:PointerEvent)=>{drag=e.clientX;renderer.domElement.setPointerCapture(e.pointerId)};const move=(e:PointerEvent)=>{if(drag!==null){turn.current+=(e.clientX-drag)*.012;drag=e.clientX}};const up=()=>{drag=null};
  renderer.domElement.addEventListener('pointerdown',down);renderer.domElement.addEventListener('pointermove',move);renderer.domElement.addEventListener('pointerup',up);renderer.domElement.addEventListener('pointercancel',up);
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const render=(t:number)=>{frame=requestAnimationFrame(render);if(document.hidden||t-last<50)return;last=t;const next=JSON.stringify(latest.current)+(factory?'cinematic':'standard');
   if(next!==seen){if(avatar){scene.remove(avatar);avatar.userData.dispose?.()}avatar=factory?factory.create(latest.current):human(latest.current);scene.add(avatar);seen=next}
   if(avatar){avatar.rotation.y=turn.current;avatar.userData.animate(reduced.matches?0:t/1000,0)}camera.position.set(0,1.32,zoom.current);camera.lookAt(0,1.2,0);renderer.render(scene,camera)};frame=requestAnimationFrame(render);
  return()=>{closed=true;cancelAnimationFrame(frame);observer.disconnect();avatar?.userData.dispose?.();factory?.dispose();renderer.dispose();renderer.forceContextLoss();renderer.domElement.remove()};
 },[]);
 return <section className="avatar-preview" aria-label="Avatar preview"><div ref={host} className="avatar-preview-canvas"/>{fallback&&<p className="tiny">Standard preview active. Your appearance choices still save.</p>}<div className="avatar-view-controls">{[['Front',0],['Side',Math.PI/2],['Back',Math.PI]].map(([label,value])=><button type="button" key={label} onClick={()=>turn.current=Number(value)}>{label}</button>)}<button type="button" aria-label="Rotate avatar left" onClick={()=>turn.current-=Math.PI/4}>↶</button><button type="button" aria-label="Rotate avatar right" onClick={()=>turn.current+=Math.PI/4}>↷</button></div><label className="avatar-zoom">Zoom<input aria-label="Avatar zoom" type="range" min="3.3" max="5.5" step="0.1" defaultValue="4.5" onChange={e=>zoom.current=Number(e.target.value)}/></label></section>
}
