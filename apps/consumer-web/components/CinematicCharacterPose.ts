import * as T from 'three';
import {Locomotion} from '../lib/locomotion.ts';

/** Visual-only adapter for the pilot's reduced CC0 rig. Never moves the player root. */
export function cinematicCharacterPose(model:T.Object3D, calibrated=false){
 const bones=new Map<string,T.Bone>();
 model.traverse(object=>{if(object instanceof T.Bone)bones.set(object.name,object)});
 const required=['head','spine01','upperarm01L','upperarm01R','lowerarm01L','lowerarm01R','upperleg01L','upperleg01R','lowerleg01L','lowerleg01R'];
 if(required.some(name=>!bones.has(name)))throw Error('Unsupported cinematic character rig');
 const bone=(name:string)=>bones.get(name)!;
 const gait=new Locomotion();
 const turn=(name:string,x:number,y:number,z:number,blend:number)=>{
  const rotation=bone(name).rotation;
  rotation.x+=(x-rotation.x)*blend;rotation.y+=(y-rotation.y)*blend;rotation.z+=(z-rotation.z)*blend;
 };
 const standing=(blend:number)=>{
  for(const side of ['L','R']){
   const sign=side==='L'?1:-1;
   turn('upperarm01'+side,0,0,-sign*.65,blend);
   turn('lowerarm01'+side,-.10,0,0,blend);
   turn('upperleg01'+side,0,0,-sign*.10,blend);
   turn('lowerleg01'+side,0,0,0,blend);
  }
 };
 standing(1);
 return {
  animate(time:number,speed:number,mode?:string,emote='',speaking=false){
   const {phase,run,weight,dt}=gait.update(time,speed,mode,calibrated);
   const blend=1-Math.exp(-24*dt);
   for(const [i,side] of ['L','R'].entries()){
    const sign=side==='L'?1:-1,p=phase+i*Math.PI;
    const step=Math.sin(p)*(.5+run*.27)*weight;
    turn('upperleg01'+side,step,0,-sign*.10,blend);
    turn('lowerleg01'+side,(Math.max(0,-Math.sin(p))*(.45+run*1.1)+run*.12)*weight,0,0,blend);
    turn('upperarm01'+side,-step*(.65+run*.45),0,-sign*(.65-run*.04),blend);
    turn('lowerarm01'+side,-.10-run*.9,0,0,blend);
   }
   model.position.y+=(Math.abs(Math.sin(phase))*(.026+run*.055)*weight+Math.sin(time*1.8)*.009*(1-weight)-model.position.y)*blend;
   model.position.z+=(0-model.position.z)*blend;
   model.rotation.x+=((emote==='collect'?.25:run*.15*weight)-model.rotation.x)*blend;
   model.rotation.y=Math.sin(phase)*.025*weight;
   model.rotation.z=Math.sin(phase)*(.018+run*.014)*weight;
   turn('head',speaking?Math.sin(time*7)*.035:-run*.06,weight<.1?Math.sin(time*.7)*.055:0,0,blend);
   if(emote==='wave'){
    turn('upperarm01R',0,0,-1.7+Math.sin(time*8)*.15,blend);
    turn('lowerarm01R',-.5,0,0,blend);
   }
  },
  sit(){
   standing(1);
   for(const side of ['L','R']){bone('upperleg01'+side).rotation.x=-1.3;bone('lowerleg01'+side).rotation.x=1.3;bone('upperarm01'+side).rotation.x=-.3}
   model.rotation.set(0,0,0);model.position.set(0,-.35,0);
  },
  cycle(time:number,speed:number){
   standing(1);
   const pedal=Math.sin(time*8)*Math.min(.25,Math.max(0,speed)*.05);
   for(const [i,side] of ['L','R'].entries()){bone('upperleg01'+side).rotation.x=-.7+(i?-pedal:pedal);bone('lowerleg01'+side).rotation.x=.9;bone('upperarm01'+side).rotation.x=-.8}
   model.rotation.set(0,0,0);model.position.set(0,-.22,-.2);
  },
  swim(time:number){
   standing(1);model.rotation.set(-Math.PI/2,0,0);model.position.set(0,-.1,0);
   for(const [i,side] of ['L','R'].entries()){bone('upperarm01'+side).rotation.x=time*3+i*Math.PI;bone('upperleg01'+side).rotation.x=Math.sin(time*5+i*Math.PI)*.2}
  }
 };
}
