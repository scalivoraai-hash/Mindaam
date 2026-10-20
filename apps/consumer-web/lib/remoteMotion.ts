type Sample={x:number;z:number;y?:number;sampled_at?:number;last_move?:number;speed?:number;mode?:string;vehicle?:{id:string;kind:string;x:number;z:number;heading:number;speed?:number;sampled_at?:number}|null};
/** Short bounded prediction between existing socket snapshots, followed by damping.
 * Authority, stops and transport changes always win. No position is sent upstream. */
export class RemoteMotion {
 x=0;z=0;y=0;heading=0;speed=0;
 private latest:Sample|null=null;private received=0;private vx=0;private vz=0;private moving=false;
 update(sample:Sample,now:number,dt:number){
  const previous=this.latest,vehicle=sample.vehicle;
  const x=vehicle&&vehicle.kind!=='bus'?vehicle.x:sample.x,z=vehicle&&vehicle.kind!=='bus'?vehicle.z:sample.z;
  if(!previous){this.x=x;this.z=z;this.y=sample.y||0;this.heading=vehicle?.heading||0}
  if(!previous||sample.sampled_at!==previous.sampled_at||sample.last_move!==previous.last_move){
   const gap=Math.max(.05,Math.min(1,(sample.sampled_at||now)-(previous?.sampled_at||now-.5)));
   const changed=vehicle?.id!==previous?.vehicle?.id;
   this.vx=previous&&!changed?(x-previous.x)/gap:0;this.vz=previous&&!changed?(z-previous.z)/gap:0;
   if(vehicle&&vehicle.kind!=='bus'){this.vx=Math.sin(vehicle.heading)*(vehicle.speed||0);this.vz=Math.cos(vehicle.heading)*(vehicle.speed||0)}
   this.moving=(vehicle?.speed??sample.speed??Math.hypot(this.vx,this.vz))>.05;
   if(!this.moving){this.vx=0;this.vz=0}
   this.latest={...sample,x,z};this.received=now;
   if(changed){this.x=x;this.z=z;this.speed=0}
  }
  // Cover the existing 500 ms snapshot interval, then freeze prediction on loss.
  const age=Math.max(0,now-this.received),predict=Math.min(.55,age);
  const tx=x+this.vx*predict,tz=z+this.vz*predict,blend=1-Math.exp(-Math.min(.1,dt)*(vehicle?22:14));
  const dx=(tx-this.x)*blend,dz=(tz-this.z)*blend;
  this.x+=dx;this.z+=dz;this.y+=((sample.y||0)-this.y)*blend;
  const actual=Math.hypot(dx,dz)/Math.max(.001,dt);
  this.speed+=(actual-this.speed)*(1-Math.exp(-dt*7));
  if(vehicle||actual>.05){const goal=vehicle?.heading??Math.atan2(dx,dz);this.heading+=Math.atan2(Math.sin(goal-this.heading),Math.cos(goal-this.heading))*blend}
  return this;
 }
}
