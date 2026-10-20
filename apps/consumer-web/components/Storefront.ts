import * as T from 'three';
import {box} from './WorldAssets';
import {Data} from '@/lib/api';
// Owned overlay geometry: never edits or extracts provider meshes.
export function storefront(b:Data){
 const g=new T.Group(),style=b.signage||{},w=style.frontage_width||6,c=style.colour||'#245b62';
 box(g,'#f1ddbc',0,1.9,-.3,w,3.8,.5);box(g,c,0,3.1,.1,w+.2,.9,.2);
 box(g,'#91d6df',-w*.27,1.65,.05,w*.32,2.1,.16);box(g,'#91d6df',w*.27,1.65,.05,w*.32,2.1,.16);
 box(g,'#6d4938',0,1.25,.1,1.15,2.5,.2);box(g,'#badfe1',0,1.55,.22,.88,1.5,.03);box(g,'#f8d68c',.38,1.1,.25,.08,.18,.07);
 box(g,c,0,2.65,.7,w,.15,1.3);box(g,'#dfccaa',0,.1,1,w+.6,.2,2);
 const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=160;const ctx=canvas.getContext('2d')!;ctx.fillStyle=c;ctx.fillRect(0,0,1024,160);ctx.fillStyle='#fff9e9';ctx.textAlign='center';ctx.textBaseline='middle';let size=76;ctx.font=`700 ${size}px sans-serif`;while(ctx.measureText(b.name).width>940&&size>22){size-=2;ctx.font=`700 ${size}px sans-serif`}ctx.fillText(b.name,512,80);
 const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;const fascia=new T.Mesh(new T.PlaneGeometry(w,.85),new T.MeshBasicMaterial({map:texture}));fascia.position.set(0,3.1,.22);g.add(fascia);
 const category=style.category||'General Store';if(['Cafe','Restaurant'].includes(category)){for(const x of [-w*.38,w*.38]){box(g,'#b27d4b',x,.8,1.8,1,.1,1);box(g,'#3f4d48',x,.4,1.8,.15,.8,.15);}}else if(category==='Gym'){for(const x of [-w*.3,w*.3]){box(g,'#324553',x,.9,.4,.7,1.2,.15)}}else{for(const x of [-w*.3,w*.3])box(g,'#ffe6a1',x,1.4,.17,.65,.8,.02)}
 if(b.visit_reward>0||b.offer_count){const badge=box(g,'#f6c758',w*.38,3.9,.1,.65,.65,.2);badge.rotation.z=.15;}
 g.userData.business=b;g.userData.dispose=()=>{texture.dispose();g.traverse(o=>{if(o instanceof T.Mesh){if(!o.geometry.userData.shared)o.geometry.dispose();if(o===fascia)(o.material as T.Material).dispose()}})};
 return g;
}
