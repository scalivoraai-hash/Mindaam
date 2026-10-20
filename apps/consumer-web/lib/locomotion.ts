/** Continuous distance-driven gait. Network packets never restart its phase. */
export class Locomotion {
 phase=0; speed=0; run=0; weight=0; last:number|undefined;
 update(time:number,speed:number,mode?:string,calibrated=false){
  const dt=this.last===undefined?1/60:Math.min(.1,Math.max(0,time-this.last));this.last=time;
  const blend=1-Math.exp(-dt*10);
  this.speed+=(Math.max(0,Math.min(calibrated?45:13,speed))-this.speed)*blend;
  this.run+=((mode?mode==='run':this.speed>7)?1-this.run:-this.run)*blend;
  this.weight+=(Math.min(1,this.speed/.9)-this.weight)*blend;
  // Longer flight stride and bent knees distinguish running from a faster walk.
  const stride=2.4+this.run*1.7;
  this.phase=(this.phase+(calibrated?Math.min(2.6,this.speed/(stride*3)):this.speed/stride)*Math.PI*2*dt)%(Math.PI*2);
  return {phase:this.phase,run:this.run,weight:this.weight,dt};
 }
}
