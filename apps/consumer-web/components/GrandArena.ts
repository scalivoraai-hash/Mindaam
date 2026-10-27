import * as T from 'three';
import {box,mesh,human,bench} from './WorldAssets';
import {Data} from '../lib/api';
/** Reuses the city's existing auditorium reservation and event entry workflow. */
export function grandArena(arena:Data){
 const g=new T.Group();g.position.set(arena.x,0,arena.z);g.rotation.y=arena.heading;
 const entrance=new T.Vector3(arena.entrance[0]-arena.x,0,arena.entrance[1]-arena.z).applyAxisAngle(new T.Vector3(0,1,0),-arena.heading);const end=new T.Vector3(0,0,12),length=entrance.distanceTo(end);const path=box(g,'#8b92aa',(entrance.x+end.x)/2,.025,(entrance.z+end.z)/2,4,.05,length);path.rotation.y=Math.atan2(entrance.x-end.x,entrance.z-end.z);
 box(g,'#1c2946',0,3.8,-1,18,7.6,14);box(g,'#263a64',0,.05,10,24,.1,8);
 const roof=mesh(new T.SphereGeometry(1,24,10,0,Math.PI*2,0,Math.PI/2),'#3a4271',g,0,7.6,-1);roof.scale.set(10,3,8);
 const glass=new T.MeshStandardMaterial({color:'#63bde5',metalness:.5,roughness:.2});glass.userData.cityOwned=true;
 const facade=new T.Mesh(new T.BoxGeometry(16,5.6,.16),glass);facade.position.set(0,3.4,6.1);g.add(facade);
 for(const x of [-7,-3,3,7])box(g,'#b1cef1',x,3.4,6.3,.12,5.8,.2);
 box(g,'#0a1029',0,1.7,6.4,3,3.4,.2);box(g,'#d8eeff',0,3.5,7,4,.2,1.7);
 for(const [i,color] of ['#0787f8','#8423f4','#ff0d9b','#00c7ec'].entries()){
  const m=new T.MeshBasicMaterial({color});m.userData.cityOwned=true;const light=new T.Mesh(new T.BoxGeometry(4.5,.13,.2),m);light.position.set(-6.75+i*4.5,7.4,6.2);g.add(light);
 }
 const neighbours:T.Group[]=[];if(arena.events?.some((e:Data)=>e.visibility==='public'))for(let i=0;i<3;i++){const npc=human({color:['#955fae','#3c8d99','#ce8368'][i]});npc.position.set(i===2?8:-8+i*2,0,11);npc.rotation.y=i===2?Math.PI/2:i%2?1:-1;g.add(npc);neighbours.push(npc);}bench(g,8,11,Math.PI/2);for(const x of [-10,10]){box(g,'#53618c',x,.6,8,1,1.2,1);mesh(new T.SphereGeometry(.8,8,5),'#518566',g,x,1.7,8);}
 const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=512;const c=canvas.getContext('2d')!;
 const gradient=c.createLinearGradient(0,0,1024,512);gradient.addColorStop(0,'#13234e');gradient.addColorStop(1,'#592b82');c.fillStyle=gradient;c.fillRect(0,0,1024,512);c.fillStyle='#78e9ff';c.font='bold 42px sans-serif';c.fillText('MINDAAM GRAND ARENA',38,75,950);c.fillStyle='#e8efff';c.font='24px sans-serif';c.fillText('One World. Every City. Your Stage.',38,118);
 const event=arena.events?.find((e:Data)=>e.status==='live')||arena.events?.[0];c.fillStyle='#fff';c.font='bold 48px sans-serif';c.fillText(event?.title||'Your next event starts here',38,235,950);c.font='28px sans-serif';c.fillText(event?`Hosted by ${event.host}`:'Concerts · Community · Presentations',38,290,950);if(event){c.font='24px sans-serif';c.fillText(`${event.ticket_price?event.ticket_price+' PC':'Free'} · ${event.available} available · ${event.visibility}`,38,335,950);c.fillText(new Date(event.starts_at*1000).toLocaleString(),38,375,950);}c.fillStyle='#8bf4dd';c.font='bold 32px sans-serif';c.fillText(event?(event.status==='live'?'LIVE NOW · View event':'UPCOMING · View event'):'BOOK THIS ARENA',38,422,950);
 const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;const mat=new T.MeshBasicMaterial({map:texture});mat.userData.cityOwned=true;const board=new T.Mesh(new T.PlaneGeometry(11,5.5),mat);board.position.set(0,11.4,1);g.add(board);
 g.userData.tick=(seconds:number,distance:number)=>{neighbours.forEach((npc,i)=>{npc.userData.setLOD?.(distance);npc.userData.animate?.(seconds+i,0);if(i===2)npc.userData.sit?.();});};
 g.userData.cityAction=()=>window.dispatchEvent(new CustomEvent('pulse-open-event',{detail:event?.id||''}));
 return g;
}
