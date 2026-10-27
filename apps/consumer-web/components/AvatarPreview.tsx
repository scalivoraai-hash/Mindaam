'use client';
import {useEffect,useRef,useState} from 'react';
import * as T from 'three';
import {human,type Appearance} from './WorldAssets';
export default function AvatarPreview({appearance}:{appearance:Appearance}){
 const host=useRef<HTMLDivElement>(null),turn=useRef(.15),[fallback,setFallback]=useState(false);
 const key=JSON.stringify([appearance.color,appearance.skin,appearance.hair,appearance.pants,appearance.style]);
 const latest=useRef(appearance),latestKey=useRef(key);latest.current=appearance;latestKey.current=key;
 useEffect(()=>{const element=host.current;if(!element)return;let renderer:T.WebGLRenderer;try{renderer=new T.WebGLRenderer({antialias:true,alpha:true})}catch{setFallback(true);return}setFallback(false);renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;element.append(renderer.domElement);
 const scene=new T.Scene();let avatar=human(latest.current),seen=latestKey.current;scene.add(avatar);scene.add(new T.HemisphereLight('#f0f7ff','#655444',2.1));const light=new T.DirectionalLight('#fff1df',2.7);light.position.set(3,4,4);scene.add(light);const fill=new T.DirectionalLight('#8acfff',1.2);fill.position.set(-3,2,-1);scene.add(fill);
 const camera=new T.PerspectiveCamera(34,1,.1,20);camera.position.set(0,1.3,4.6);camera.lookAt(0,1.22,0);const resize=()=>{const w=element.clientWidth,h=element.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()};const observer=new ResizeObserver(resize);observer.observe(element);resize();const reduced=matchMedia('(prefers-reduced-motion: reduce)');let frame=0,last=0;const render=(t:number)=>{frame=requestAnimationFrame(render);if(document.hidden||t-last<33)return;last=t;if(seen!==latestKey.current){scene.remove(avatar);avatar=human(latest.current);scene.add(avatar);seen=latestKey.current}avatar.rotation.y=turn.current;avatar.userData.animate(reduced.matches?0:t/1000,0);renderer.render(scene,camera)};frame=requestAnimationFrame(render);
 return()=>{cancelAnimationFrame(frame);observer.disconnect();renderer.dispose();renderer.forceContextLoss();renderer.domElement.remove()};
 },[]);
 return <section className="avatar-preview" aria-label="Avatar preview"><div ref={host} className="avatar-preview-canvas"/>{fallback&&<p>3D preview is unavailable in this browser. Your appearance choices still save.</p>}<div className="actions"><button type="button" aria-label="Rotate avatar left" onClick={()=>turn.current-=Math.PI/4}>↶ Rotate</button><button type="button" aria-label="Rotate avatar right" onClick={()=>turn.current+=Math.PI/4}>Rotate ↷</button></div></section>
}
