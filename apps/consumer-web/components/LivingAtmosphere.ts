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
 const rainPositions=new Float32Array(count*6),rainGeometry=new T.BufferGeometry();rainGeometry.setAttribute('position',new T.BufferAttribute(rainPositions,3));ownedGeometry.add(rainGeometry);
 const rainMaterial=new T.LineBasicMaterial({color:'#c4dce9',transparent:true,opacity:.65,depthWrite:false});ownedMaterials.add(rainMaterial);
 const rain=new T.LineSegments(rainGeometry,rainMaterial);rain.name='Falling rain streaks';rain.frustumCulled=false;root.add(rain);
 const splashGeometry=new T.RingGeometry(.045,.065,6),splashMaterial=new T.MeshBasicMaterial({color:'#b9d2db',transparent:true,opacity:.32,depthWrite:false,side:T.DoubleSide});ownedGeometry.add(splashGeometry);ownedMaterials.add(splashMaterial);
 const splashes=new T.InstancedMesh(splashGeometry,splashMaterial,80);splashes.name='Rain ground splashes';splashes.frustumCulled=false;root.add(splashes);const splashPose=new T.Object3D();
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
  if(kind===0&&i!==8){g.userData.birds=[];for(let b=0;b<(i===0?2:7);b++){const bird=new T.Group();mesh(new T.SphereGeometry(1,8,5),'#33404b',bird,0,0,0).scale.set(.14,.13,.45);const wings:T.Group[]=[];for(const side of [-1,1]){const wing=new T.Group();wing.position.x=side*.1;const wingMesh=mesh(new T.BoxGeometry(.7,.035,.22),'#394856',wing,side*.32,0,0);wingMesh.rotation.y=side*.25;bird.add(wing);wings.push(wing);}bird.position.set((b%3)*2.7,Math.sin(b)*1.1,Math.floor(b/3)*3.1);bird.scale.setScalar(i===0?1.5:1);g.add(bird);g.userData.birds.push({bird,wings,phase:b*1.9});}}
  if(kind===1){mesh(new T.SphereGeometry(1,12,8),'#dce8f7',g,0,0,0).scale.set(.55,.55,5);const wing=box(g,'#c1d2ec',0,0,0,12,.12,1.5);wing.rotation.y=.08;box(g,'#9daecc',0,1,-3.8,.15,2,1.5);box(g,'#c1d2ec',0,.3,-3.8,4,.1,.8);const lights=new T.Group();for(const side of [-1,1]){const mat=new T.MeshBasicMaterial({color:side<0?'#e88b85':'#8be4b5'});ownedMaterials.add(mat);const light=new T.Mesh(new T.SphereGeometry(.12,6,4),mat);ownedGeometry.add(light.geometry);light.position.set(side*6,0,0);lights.add(light);}g.add(lights);g.userData.navigationLights=lights;}
  if(kind===2){for(let panel=0;panel<8;panel++){const balloon=mesh(new T.SphereGeometry(4,4,8,panel*Math.PI/4,Math.PI/4),panel%2?'#e2c797':['#a46ad2','#c88e62','#69a4a3'][Math.floor(i/4)],g,0,2,0);balloon.scale.y=1.2;}box(g,'#9c775b',0,-3.8,0,1.4,1,1.4);for(const x of [-.6,.6])box(g,'#bca37c',x,-2.7,0,.04,1.5,.04);}
  if(kind===3){mesh(new T.SphereGeometry(1,10,6),'#639baa',g,0,0,0).scale.set(1,.9,1.6);box(g,'#506a86',0,0,-2,.4,.4,4);g.userData.rotor=box(g,'#384b66',0,1.3,0,7,.08,.2);}
 }
 const parachutist=new T.Group();parachutist.name='Ambient parachutist';root.add(parachutist);const canopy=new T.Group();parachutist.add(canopy);const sail=mesh(new T.SphereGeometry(3,12,6,0,Math.PI*2,0,Math.PI/2),'#cb925a',canopy,0,3,0);sail.scale.set(1,.6,.7);for(const x of [-2,2]){const line=box(canopy,'#dfddd2',x*.5,1,0,.025,4,.025);line.rotation.z=-x*.24;}box(parachutist,'#344a66',0,-1,0,.38,.8,.3);for(const x of [-.13,.13])box(parachutist,'#2d3d4f',x,-1.6,0,.12,.55,.12);
 const jumpPlane=new T.Group();jumpPlane.name='Parachutist arrival aircraft';root.add(jumpPlane);box(jumpPlane,'#d7dee4',0,0,0,1,1,7);box(jumpPlane,'#aabac9',0,0,0,9,.15,1.2);
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
  particles.visible=state.snow||state.weather==='Windy';particles.position.set(player.x,0,player.z);
  const particleCount=Math.max(24,Math.floor(budget.particles*(['Light rain','Light snow'].includes(state.weather)?.45:1)*(reduce?.35:1)));geometry.setDrawRange(0,particleCount);particleMaterial.size=state.snow?.22:.12;
  particleMaterial.color.set(state.weather==='Windy'?'#bd8645':'#e0efff');const fall=state.snow||state.weather==='Windy'?2:state.weather==='Light rain'?15:22;
  rain.visible=state.rain;splashes.visible=state.rain;rain.position.set(player.x,player.y,player.z);rainGeometry.setDrawRange(0,particleCount*2);rainMaterial.opacity=state.night?.5:state.weather==='Light rain'?.55:.72;
  if(particles.visible||rain.visible){for(let i=0;i<particleCount;i++){
   positions[i*3+1]=((positions[i*3+1]-fall*dt)%40+40)%40;positions[i*3]=((positions[i*3]+50+dt*state.wind*2)%100+100)%100-50;
   const x=positions[i*3]*.28,y=positions[i*3+1]*.6,z=positions[i*3+2]*.28,length=state.weather==='Light rain'?.55:.95;
   rainPositions.set([x,y,z,x-state.wind*.12,y+length,z],i*6);
  }geometry.attributes.position.needsUpdate=true;rainGeometry.attributes.position.needsUpdate=true;}
  splashes.count=reduce?12:quality==='low'?20:quality==='balanced'?45:80;
  if(state.rain)for(let i=0;i<splashes.count;i++){const age=(seconds*1.7+random(i*103))%1;splashPose.position.set(player.x+(random(i*67)-.5)*20,.035,player.z+(random(i*71)-.5)*20);splashPose.rotation.x=-Math.PI/2;splashPose.scale.setScalar(age<.65?.5+age*3:0);splashPose.updateMatrix();splashes.setMatrixAt(i,splashPose.matrix);}splashes.instanceMatrix.needsUpdate=true;
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
  skyObjects.forEach((g,i)=>{const age=((seconds+i*29+seed%120)%120)/120,kind=i%4;g.visible=i<budget.sky&&age<.82&&(i!==8||state.seasonIndex===0||state.weather==='Windy');
   const x=(age-.41)*(kind===2?160:kind===0?280:650),z=-70+(i%3)*37+Math.sin(age*Math.PI*2+i)*12;
   g.position.set(player.x+x,kind===0?25+i*2+Math.sin(age*6+i)*5:45+kind*16+Math.sin(age*5+i)*3,player.z+z);g.rotation.y=Math.PI/2+Math.cos(age*Math.PI*2+i)*.12;
   if(g.userData.rotor)g.userData.rotor.rotation.y=seconds*(reduce?5:24);if(g.userData.navigationLights)g.userData.navigationLights.visible=state.night;
   if(i===0&&g.userData.birds)g.userData.birds[1].bird.visible=Math.floor(seconds/120)%2===0;
   for(const {bird,wings,phase} of g.userData.birds||[]){const flap=Math.sin(seconds*(reduce?2:6)+phase)*(Math.sin(seconds*.4+phase)>.2?.55:.08);wings[0].rotation.z=flap;wings[1].rotation.z=-flap;bird.rotation.y=Math.sin(seconds*.35+phase)*.1;}
  });
  const jumpAge=((seconds+seed%240)%240)/240;parachutist.visible=quality!=='low'&&!state.rain&&jumpAge<.65;
  // An off-screen landing avoids any invented landing permission or collision with people.
  const descent=Math.min(1,jumpAge/.65);parachutist.position.set(player.x-100+descent*240,100-descent*62,player.z-140-descent*130);parachutist.rotation.z=Math.sin(seconds*.7)*.05;canopy.scale.setScalar(Math.min(1,Math.max(.01,(descent-.025)*12)));jumpPlane.position.set(player.x-100+descent*500,105,player.z-140);jumpPlane.visible=parachutist.visible&&descent<.35;

  return state;
 }
 return {update,dispose(){scene.remove(root);promoTexture.dispose();root.traverse(o=>{if(o instanceof T.Mesh){if(!o.geometry.userData.shared)ownedGeometry.add(o.geometry);for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.userData.cityOwned)ownedMaterials.add(m);}});ownedGeometry.forEach(g=>g.dispose());ownedMaterials.forEach(m=>m.dispose());}};
}
