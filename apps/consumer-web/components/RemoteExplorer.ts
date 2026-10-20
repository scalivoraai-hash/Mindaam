import * as T from 'three';
import {human,car,bicycle,motorbike,box} from './WorldAssets';
import {RemoteMotion} from '../lib/remoteMotion';

/** A single transform owns both the remote driver and their existing vehicle mesh. */
export function remoteExplorer(appearance:Record<string,string>){
 const root=new T.Group(),avatar=human(appearance,true),motion=new RemoteMotion();root.add(avatar);
 let vehicle:T.Group|null=null,kind='';
 root.userData.avatar=avatar;
 root.userData.update=(player:any,time:number,dt:number,bus?:T.Group)=>{
  const next=player.vehicle?.kind||'';
  if(next!==kind){
   if(vehicle){vehicle.traverse(o=>{if(o instanceof T.Mesh&&!o.geometry.userData.shared)o.geometry.dispose();if(o instanceof T.Mesh&&o.userData.ownedMaterial)(o.material as T.Material).dispose()});root.remove(vehicle)}
   vehicle=null;kind=next;
   if(kind&&kind!=='bus'&&kind!=='swim'){
    vehicle=new T.Group();vehicle.name='remote-vehicle-'+kind;root.add(vehicle);
    if(kind==='car'){const model=car(vehicle,0,0,0,'#385968');const glass=model.getObjectByName('vehicle-glazing') as T.Mesh;const finish=(glass.material as T.MeshStandardMaterial).clone();finish.transparent=true;finish.opacity=.34;finish.depthWrite=false;glass.material=finish;glass.userData.ownedMaterial=true;}
    else if(kind==='scooter')motorbike(vehicle);
    else if(kind==='bike'||kind==='ebike')bicycle(vehicle);
    else if(kind==='boat'){box(vehicle,'#6a9ea6',0,.4,0,2,.6,4);box(vehicle,'#e4ded0',0,.8,0,1.5,.2,2.8)}
   }
  }
  const pose=motion.update(player,time,dt);
  root.position.set(pose.x,pose.y,pose.z);root.rotation.set(0,pose.heading,0);
  avatar.position.set(0,0,0);avatar.scale.setScalar(1);
  avatar.userData.speaking=root.userData.speaking;
  avatar.userData.animate(time,pose.speed,player.mode);
  if(['bike','ebike','scooter'].includes(kind)){avatar.position.y=.2;avatar.userData.cycle(time,player.vehicle.speed||0)}
  if(kind==='car'){avatar.userData.sit();avatar.scale.setScalar(.70);avatar.position.set(-.36,.03,.05)}
  if(kind==='boat'){avatar.userData.sit();avatar.position.y=.65}
  if(kind==='swim'){avatar.userData.swim(time);avatar.position.y=.2}
  if(kind==='bus'){
   if(bus){
    // Seat offset and bus share exactly one rendered transform, including turns.
    const v=player.vehicle,offset=new T.Vector3(player.x-v.x,player.y||.95,player.z-v.z);
    offset.applyAxisAngle(new T.Vector3(0,1,0),bus.rotation.y-v.heading);
    root.position.copy(bus.position).add(offset);root.rotation.y=bus.rotation.y;
   }
   if(player.seated)avatar.userData.sit();
  }
  root.userData.person=player;root.userData.movementState=player.movement_state;
 };
 root.userData.setLOD=(distance:number)=>avatar.userData.setLOD(distance);
 root.userData.dispose=()=>root.traverse(o=>{if(o instanceof T.Mesh&&!o.geometry.userData.shared)o.geometry.dispose();if(o instanceof T.Mesh&&o.userData.ownedMaterial)(o.material as T.Material).dispose()});
 return root;
}
