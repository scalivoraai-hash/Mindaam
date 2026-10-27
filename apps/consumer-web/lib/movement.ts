import movement from '../../../shared/movement.json' with {type:'json'};
export const MOVEMENT=movement;
export const WALK_SPEED=movement.previewStep/(movement.inputIntervalMs/1000);
export const RUN_SPEED=WALK_SPEED*movement.runMultiplier;
export const OUTDOOR_WALK_SPEED=WALK_SPEED*movement.normalWorldMultiplier*movement.outdoorWalkFactor;
export const OUTDOOR_RUN_SPEED=RUN_SPEED*movement.normalWorldMultiplier;
export function cameraRelative(x:number,z:number,angle:number){const length=Math.max(1,Math.hypot(x,z));return {x:(Math.cos(angle)*x+Math.sin(angle)*z)/length,z:(-Math.sin(angle)*x+Math.cos(angle)*z)/length}}

/** One held-input policy for keyboard and joystick; explicit Run remains an override. */
export class HeldMovement {
 private since:number|null=null;
 update(x:number,z:number,now:number,explicitRun=false){
  const strength=Math.hypot(x,z);
  if(strength<MOVEMENT.joystickDeadzone){this.since=null;return {x:0,z:0,mode:'walk'}}
  if(strength<MOVEMENT.joystickRunThreshold)this.since=null;
  else this.since ??= now;
  const run=explicitRun||(this.since!==null&&now-this.since>=MOVEMENT.holdToRunMs);
  const length=Math.max(1,strength);
  return {x:x/length,z:z/length,mode:run?'run':'walk'};
 }
 reset(){this.since=null}
}
