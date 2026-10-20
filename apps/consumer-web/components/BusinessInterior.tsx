'use client';
import {useEffect,useRef,useState} from 'react';
import * as T from 'three';
import {box} from './WorldAssets';
import {Data} from '@/lib/api';
export default function BusinessInterior({business}:{business:Data}){
 const host=useRef<HTMLDivElement>(null),[fallback,setFallback]=useState(false);const s=business.signage||{},category=s.category||'General Store';
 useEffect(()=>{if(!host.current)return;const el=host.current;let renderer:T.WebGLRenderer;try{renderer=new T.WebGLRenderer({antialias:true,alpha:true})}catch{setFallback(true);return}setFallback(false);renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));el.appendChild(renderer.domElement);const scene=new T.Scene(),room=new T.Group();scene.add(room);scene.add(new T.HemisphereLight('#fff3dc','#526672',3));const camera=new T.PerspectiveCamera(44,1,.1,60);camera.position.set(9,9,12);camera.lookAt(0,1,0);box(room,'#d2b795',0,-.15,0,12,.3,9);box(room,s.colour||'#245b62',0,2,-4.5,12,4,.2);box(room,'#eadfc9',-6,2,0,.2,4,9);box(room,'#755641',0,1,-2,7,2,1.4);
 const table=(x:number,z:number)=>{box(room,'#996840',x,.9,z,1.5,.15,1.5);box(room,'#344b53',x,.45,z,.16,.9,.16);for(const dx of [-1,1])box(room,s.colour||'#245b62',x+dx,.55,z,.65,1.1,.65)};
 if(['Cafe','Restaurant'].includes(category)){table(-3,1.5);table(2,1.5);if(category==='Restaurant')table(3,-1);}
 else if(category==='Gym'){for(const x of [-3,0,3]){box(room,'#344b53',x,.25,1,1.4,.4,2.5);box(room,'#596d73',x,1,0,.15,1.5,.15);box(room,'#202d38',x,1.5,0,1.2,.3,.25)}}
 else if(category==='Salon'){for(const x of [-3,0,3]){box(room,'#b8dce4',x,2,-4.3,1.6,2,.1);box(room,s.colour||'#245b62',x,.65,-.2,1,1.3,1)}}
 else if(category==='Professional Services'){table(-2,1);box(room,'#344b53',-2,1.3,1,1,.65,.1);box(room,'#ddd4bf',4,1,-2,2,2,.5)}
 else if(category==='Entertainment'){for(const x of [-3,0,3]){box(room,s.colour||'#245b62',x,1.3,1,1.3,2.6,1);box(room,'#99deec',x,1.8,1.55,1,.8,.08)}}
 else{for(const x of [-4,4])for(const y of [.6,1.4,2.2]){box(room,'#9c7956',x,y,0,1.7,.12,4);for(const z of [-1,0,1])box(room,s.colour||'#245b62',x,y+.25,z,.5,.5,.5)}}
 const resize=()=>{renderer.setSize(el.clientWidth,260);camera.aspect=el.clientWidth/260;camera.updateProjectionMatrix();renderer.render(scene,camera)};const observer=new ResizeObserver(resize);observer.observe(el);resize();return()=>{observer.disconnect();scene.traverse(o=>{if(o instanceof T.Mesh&&!o.geometry.userData.shared)o.geometry.dispose()});renderer.dispose();renderer.domElement.remove()};
 },[business.id,category,s.colour]);
 return <section className="business-interior"><div ref={host} aria-label={`${category} virtual interior`}/>{fallback&&<div className="interior-fallback" style={{borderColor:s.colour||'#245b62'}}><span>{category==='Cafe'?'☕':category==='Restaurant'?'🍽':category==='Gym'?'🏋':category==='Salon'?'✂':'🏪'}</span><h3>{business.name}</h3><p>{category}</p></div>}<small>Virtual {category.toLowerCase()} · illustrative layout</small></section>
}
