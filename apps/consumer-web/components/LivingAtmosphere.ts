import * as T from 'three';
import {climateAt,citySeed,QUALITY,routePose,trafficPose,trafficRoads,nextTrafficRoad,type RoadFeature,type WorldQuality} from '../lib/worldClimate';
import {car,bicycle,motorbike,human,box,mesh} from './WorldAssets';

/** Cosmetic city activity: bounded entities, no presence records, rewards, RPCs or database writes. */
export function livingAtmosphere(scene:T.Scene,city:string,features:RoadFeature[],sun:T.DirectionalLight,origin:number[]=[0,0]){
 const root=new T.Group();root.name='Ambient city (NPCs)';scene.add(root);
 const ownedMaterials=new Set<T.Material>(),ownedGeometry=new Set<T.BufferGeometry>();
 const count=QUALITY.high.particles,positions=new Float32Array(count*3),seed=citySeed(city);
 const random=(i:number)=>{let n=(i+seed)|0;n=Math.imul(n^(n>>>16),0x45d9f3b);n=Math.imul(n^(n>>>16),0x45d9f3b);return ((n^(n>>>16))>>>0)/4294967296;};
 for(let i=0;i<count;i++){positions[i*3]=(random(i*7)-.5)*100;positions[i*3+1]=random(i*11)*40;positions[i*3+2]=(random(i*17)-.5)*100;}
 const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.BufferAttribute(positions,3));ownedGeometry.add(geometry);
 const particleMaterial=new T.PointsMaterial({color:'#e0efff',size:.12,transparent:true,opacity:.7,depthWrite:false});ownedMaterials.add(particleMaterial);
 const particles=new T.Points(geometry,particleMaterial);particles.frustumCulled=false;root.add(particles);
 const clouds=new T.Group();root.add(clouds);
 const cloudMaterial=new T.MeshBasicMaterial({color:'#e1e7f0',transparent:true,opacity:.65,depthWrite:false});ownedMaterials.add(cloudMaterial);
 const cloudGeometry=new T.SphereGeometry(1,8,5);ownedGeometry.add(cloudGeometry);
 for(let i=0;i<12;i++){const cloud=new T.Mesh(cloudGeometry,cloudMaterial);cloud.scale.set(12+i%3*4,2,7);cloud.position.set((i%4-1.5)*65,65+i%3*7,(Math.floor(i/4)-1)*65);clouds.add(cloud);}
 const routes=trafficRoads(features).sort((a,b)=>Math.hypot(a.points[0][0]-origin[0],a.points[0][1]-origin[1])-Math.hypot(b.points[0][0]-origin[0],b.points[0][1]-origin[1]));
 const throughRoutes=routes.filter(r=>!["yes","1","true"].includes(r.tags.oneway)||nextTrafficRoad(r,routes,0));
 const vehicles=throughRoutes.filter(r=>r.length>35).slice(0,QUALITY.high.traffic).map((road,i)=>{
  const g=new T.Group();root.add(g);const kind=i%8;
  if(kind===6){const mainRoads=throughRoutes.filter(r=>r.length>35&&['primary','secondary','tertiary'].includes(r.tags.highway));road=mainRoads[Math.floor(i/8)%mainRoads.length]||road;}
  const bus=kind===6&&['primary','secondary','tertiary'].includes(road.tags.highway);
  if(bus){box(g,'#526cbd',0,1.5,0,2.4,2.6,7);box(g,'#a6dce5',0,2.1,0,2.45,.8,6);for(const x of [-1.15,1.15])for(const z of [-2.3,2.3]){const wheel=mesh(new T.CylinderGeometry(.5,.5,.22,8),'#253345',g,x,.5,z);wheel.rotation.z=Math.PI/2;wheel.userData.rollingRadius=.5;}}else if(kind===7){car(g,0,0,0,'#dadde6');box(g,'#a5adc4',0,1.7,-.8,1.7,1.6,2.2);}else if(kind===1)bicycle(g);else if(kind===2||kind===3)motorbike(g);else car(g,0,0,0,kind===4?'#e9bb45':kind===5?'#bbc9e2':['#637ea5','#de8c82','#54a6a0'][i%3]);
  const wheels:T.Object3D[]=[];g.traverse(o=>{if(o.userData.rollingRadius)wheels.push(o)});
  if(kind===1||kind===2||kind===3){const rider=human({color:'#6b72b4',skin:'#bb8966'});rider.position.y=.2;g.add(rider);rider.userData.cycle?.(0,0);g.userData.rider=rider;}
  const lamps=new T.Group();g.add(lamps);const glow=new T.MeshBasicMaterial({color:'#fff0b0'});ownedMaterials.add(glow);for(const x of [-.55,.55]){const lamp=new T.Mesh(new T.BoxGeometry(.24,.12,.08),glow);lamp.position.set(x,.9,2);lamps.add(lamp);ownedGeometry.add(lamp.geometry);}
  const distance=road.length*random(i*37),initial=trafficPose(road,distance);g.position.set(initial.x,0,initial.z);g.rotation.y=initial.heading;g.userData.ambient=true;g.userData.kind=kind===1?'bicycle':kind===2||kind===3?'motorbike':bus?'bus':'car';return {g,road,distance,wheels,total:0,speed:kind===1?3:kind===6?4:kind===4?5:7,heading:0,lamps,waitUntil:0,lastCorner:-1,parkedUntil:0,turns:0};
 });
 const puddleMaterial=new T.MeshStandardMaterial({color:'#6b8095',roughness:.22,metalness:.35,transparent:true,opacity:0,depthWrite:false});ownedMaterials.add(puddleMaterial);const puddleGeometry=new T.CircleGeometry(1,12);ownedGeometry.add(puddleGeometry);const puddles=new T.Group();root.add(puddles);routes.slice(0,12).forEach((road,i)=>{const pose=routePose(road.points,road.length*.4),p=new T.Mesh(puddleGeometry,puddleMaterial);p.rotation.x=-Math.PI/2;p.scale.set(.6+random(i)*.6,.3+random(i+1)*.3,1);p.position.set(pose.x,.045,pose.z);puddles.add(p);});
 const skyObjects:T.Group[]=[];
 for(let i=0;i<12;i++){
  const g=new T.Group();root.add(g);skyObjects.push(g);const kind=i%4;
  if(i===8){const kite=mesh(new T.PlaneGeometry(2,2),'#ebbb65',g,0,0,0);kite.rotation.z=Math.PI/4;box(g,'#e4ddce',0,-3,0,.035,5,.035);}
  if(kind===0&&i!==8){for(let b=0;b<3;b++){const bird=new T.Group();box(bird,'#33435e',0,0,0,.13,.1,.5);box(bird,'#33435e',0,0,.05,1.2,.06,.18);bird.position.set(b*2,b%2,b*1.5);g.add(bird);}}
  if(kind===1){box(g,'#dce8f7',0,0,0,1,1,9);box(g,'#c1d2ec',0,0,0,12,.15,1.6);box(g,'#9daecc',0,1,-3.8,.2,2,1.5);}
  if(kind===2){mesh(new T.SphereGeometry(4,12,8),'#a46ad2',g,0,2,0);box(g,'#9c775b',0,-3,0,1.4,1,1.4);}
  if(kind===3){mesh(new T.SphereGeometry(1,8,6),'#639baa',g,0,0,0);box(g,'#506a86',0,0,-2,.4,.4,4);box(g,'#384b66',0,1.3,0,7,.08,.2);}
 }
 const starGeometry=new T.BufferGeometry(),starPositions=new Float32Array(180*3);for(let i=0;i<180;i++){const angle=random(i*31)*Math.PI*2,r=180+random(i*53)*170;starPositions.set([Math.cos(angle)*r,90+random(i*71)*150,Math.sin(angle)*r],i*3);}starGeometry.setAttribute('position',new T.BufferAttribute(starPositions,3));ownedGeometry.add(starGeometry);const starMaterial=new T.PointsMaterial({color:'#d8e9ff',size:.6,transparent:true,opacity:.8,depthWrite:false});ownedMaterials.add(starMaterial);const stars=new T.Points(starGeometry,starMaterial);root.add(stars);
 const promoCanvas=document.createElement('canvas');promoCanvas.width=512;promoCanvas.height=160;const promoContext=promoCanvas.getContext('2d')!,promoTexture=new T.CanvasTexture(promoCanvas);promoTexture.colorSpace=T.SRGBColorSpace;const promoMaterial=new T.MeshBasicMaterial({map:promoTexture,side:T.DoubleSide});ownedMaterials.add(promoMaterial);const promoGeometry=new T.PlaneGeometry(12,3.75);ownedGeometry.add(promoGeometry);const promo=new T.Mesh(promoGeometry,promoMaterial);promo.position.set(0,-5.5,0);skyObjects[2].add(promo);let promoKey='';
 const wheelAxis=new T.Vector3(1,0,0);
 const sunColour=new T.Color(),skyColour=new T.Color(),nightSky=new T.Color('#101c3e'),daySky=new T.Color('#b5d8ed');
 
 function update(seconds:number,dt:number,player:T.Vector3,people:{x:number;z:number}[],quality:WorldQuality,reduce:boolean,events:{id:string;title:string;visibility:string}[]=[]){
  const advertised=events.find(e=>e.visibility==='public');promo.visible=!!advertised;if(advertised&&advertised.id+advertised.title!==promoKey){promoKey=advertised.id+advertised.title;promoContext.fillStyle='#18284e';promoContext.fillRect(0,0,512,160);promoContext.fillStyle='#9beeff';promoContext.font='bold 24px sans-serif';promoContext.fillText('AT MINDAAM GRAND ARENA',20,45,470);promoContext.fillStyle='#fff';promoContext.font='bold 32px sans-serif';promoContext.fillText(advertised.title,20,105,470);promoTexture.needsUpdate=true;}
  const state=climateAt(city,seconds),budget=QUALITY[quality];stars.visible=state.night;stars.position.set(player.x,0,player.z);
  skyColour.copy(state.night?nightSky:daySky);if(state.weather==='Clear')skyColour.set('#93c8ed');if(state.weather==='Overcast')skyColour.set('#9baab9');if(state.snow)skyColour.set('#c2d5e3');if(state.rain)skyColour.set('#73899c');if(state.weather==='Sunset'||state.weather==='Sunrise')skyColour.set('#dc9f9c');
  (scene.background as T.Color).lerp(skyColour,Math.min(1,dt*.3));scene.fog=null;
  sun.intensity+=((state.night?.24:state.rain?1.15:2.7)-sun.intensity)*Math.min(1,dt*.3);
  clouds.position.set(player.x,0,player.z);clouds.rotation.y=reduce?0:seconds*.001;cloudMaterial.opacity=state.weather==='Clear'?.12:state.weather==='Sunny'?.3:state.rain||state.weather==='Overcast'?.9:.6;cloudMaterial.color.set(state.weather==='Thunderclouds'?'#687587':'#e1e7f0');puddleMaterial.opacity+=((state.rain?.38:0)-puddleMaterial.opacity)*Math.min(1,dt*.3);sun.color.lerp(sunColour.set(state.night?'#7e9bd3':state.snow?'#dcecff':state.weather==='Sunset'||state.weather==='Sunrise'?'#ffc79b':'#fff3d9'),Math.min(1,dt*.3));
  particles.visible=(state.rain||state.snow||state.weather==='Windy')&&!reduce;particles.position.set(player.x,0,player.z);const particleCount=Math.floor(budget.particles*(['Light rain','Light snow'].includes(state.weather)?.4:1));geometry.setDrawRange(0,particleCount);particleMaterial.size=state.snow?.22:.09;
  particleMaterial.color.set(state.weather==='Windy'?'#bd8645':'#e0efff');const fall=state.snow||state.weather==='Windy'?2:18;
  if(particles.visible){for(let i=0;i<particleCount;i++){positions[i*3+1]=(40+positions[i*3+1]-fall*dt)%40;positions[i*3]=(50+positions[i*3]+dt*state.wind*2)%100-50;}geometry.attributes.position.needsUpdate=true;}
  // Simulation always advances. Quality and reduced effects only limit drawing/cosmetics.
  const step=Math.max(0,Math.min(dt,.1)),snapshots=vehicles.map(v=>trafficPose(v.road,v.distance));
  vehicles.forEach((v,i)=>{
   const here=snapshots[i],candidate=trafficPose(v.road,v.distance+v.speed*step);
   const pedestrian=[player,...people].some(p=>Math.hypot(p.x-candidate.x,p.z-candidate.z)<2.2);
   const blocked=pedestrian||vehicles.some((o,j)=>{
    if(i===j)return false;const other=snapshots[j],dx=other.x-here.x,dz=other.z-here.z;
    const ahead=dx*Math.sin(here.heading)+dz*Math.cos(here.heading),side=Math.abs(dx*Math.cos(here.heading)-dz*Math.sin(here.heading));
    const alignment=Math.cos(other.heading-here.heading);
    // Following traffic yields only to the vehicle ahead, never to a follower behind it.
    if(alignment>.65)return ahead>0&&ahead<(v.g.userData.kind==='bus'?9:6)&&side<1.9;
    // Junction priority is deterministic; the winner clears while crossing traffic waits.
    const approaching=-dx*Math.sin(other.heading)-dz*Math.cos(other.heading)>-1;
    return j<i&&Math.hypot(dx,dz)<7&&approaching&&ahead>-1;
   });
   v.lamps.visible=state.night;
   const advance=blocked?0:Math.min(v.speed*step,Math.max(0,v.road.length-v.distance));
   v.distance+=advance;v.total+=advance;
   if(v.distance>=v.road.length){
    const next=nextTrafficRoad(v.road,throughRoutes,seed+i+v.turns++);
    if(next){v.road=next;v.distance=0;}
    else if(!['yes','1','true'].includes(v.road.tags.oneway)){v.road={...v.road,points:[...v.road.points].reverse()};v.distance=0;}
    else if(Math.hypot(here.x-player.x,here.z-player.z)>150){v.distance=0;}
   }
   const pose=trafficPose(v.road,v.distance);v.g.position.set(pose.x,0,pose.z);
   v.g.userData.rider?.userData.cycle?.(seconds,advance?Math.min(v.speed,reduce?2:v.speed):0);
   for(const wheel of v.wheels)wheel.rotateOnWorldAxis(wheelAxis,advance/wheel.userData.rollingRadius);
   v.g.userData.travelled=v.total;v.g.userData.road=v.road.id;
   v.g.rotation.y+=Math.atan2(Math.sin(pose.heading-v.g.rotation.y),Math.cos(pose.heading-v.g.rotation.y))*Math.min(1,step*4);
   v.g.visible=i<budget.traffic&&Math.hypot(pose.x-player.x,pose.z-player.z)<150;
  });
  skyObjects.forEach((g,i)=>{const age=((seconds+i*43+seed%180)%180)/180;g.visible=!reduce&&i<budget.sky&&age<.65&&(i!==8||state.seasonIndex===0||state.weather==='Windy');g.position.set(player.x+(age-.325)*900,35+(i%4)*18,player.z-80+(i%3)*45);g.rotation.y=Math.PI/2;if(i%4===3)g.children[g.children.length-1].rotation.y=seconds*9;if(i%4===0)g.rotation.z=Math.sin(seconds*3)*.08;});
  return state;
 }
 return {update,dispose(){scene.remove(root);promoTexture.dispose();root.traverse(o=>{if(o instanceof T.Mesh){if(!o.geometry.userData.shared)ownedGeometry.add(o.geometry);for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.userData.cityOwned)ownedMaterials.add(m);}});ownedGeometry.forEach(g=>g.dispose());ownedMaterials.forEach(m=>m.dispose());}};
}
