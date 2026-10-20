export type CameraPose = { angle: number; pitch: number; zoom: number };
export const DEFAULT_CAMERA: CameraPose = { angle: .7, pitch: .35, zoom: 16.5 };
export const LOOK_SENSITIVITY = { mouse: .0022, touch: .0028 };
export const PLAYER_LOOK_SENSITIVITY = {mouse:.0012,touch:.0016};
const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v));

/** Bound interrupted pointer jumps. Ordinary drag distance is independent of event rate. */
export function dragCamera(pose: CameraPose, dx: number, dy: number, touch = false, authenticated = false): CameraPose {
  const profile=authenticated?PLAYER_LOOK_SENSITIVITY:LOOK_SENSITIVITY;
  const sensitivity = touch ? profile.touch : profile.mouse;
  return { ...pose, angle: pose.angle - clamp(dx, -80, 80) * sensitivity,
    pitch: clamp(pose.pitch + clamp(dy, -80, 80) * sensitivity * .8, .08, 1.48) };
}

export const zoomLimits=(inside=false)=>inside?{min:6,max:10}:{min:6,max:38};
export function boundedZoom(zoom:number,inside=false){const {min,max}=zoomLimits(inside);return clamp(zoom,min,max)}

/** Only canvas-owned contacts participate; ending a pinch cannot become a drag. */
export class CameraGesture {
 private pointers=new Map<number,{x:number;y:number}>();
 private pinching=false;private distance=0;
 down(id:number,x:number,y:number){this.pointers.set(id,{x,y});if(this.pointers.size===2){this.pinching=true;this.distance=this.span()}}
 private span(){const [a,b]=[...this.pointers.values()];return a&&b?Math.hypot(a.x-b.x,a.y-b.y):0}
 move(id:number,x:number,y:number){
  const previous=this.pointers.get(id);if(!previous)return null;
  this.pointers.set(id,{x,y});
  if(this.pinching){if(this.pointers.size!==2)return null;const span=this.span(),ratio=this.distance>12&&span>12?this.distance/span:1;this.distance=span;return {dx:0,dy:0,ratio:clamp(ratio,.85,1.15)}}
  return {dx:x-previous.x,dy:y-previous.y,ratio:1};
 }
 up(id:number){this.pointers.delete(id);if(!this.pointers.size)this.reset()}
 reset(){this.pointers.clear();this.pinching=false;this.distance=0}
}

/** Exponential damping has the same response at 30, 60 and 120 Hz. */
export function smoothCamera(current: CameraPose, target: CameraPose, dt: number): CameraPose {
  const alpha = 1 - Math.exp(-14 * clamp(dt, 0, .1));
  const turn = Math.atan2(Math.sin(target.angle - current.angle), Math.cos(target.angle - current.angle));
  return { angle: current.angle + turn * alpha,
    pitch: current.pitch + (target.pitch - current.pitch) * alpha,
    zoom: current.zoom + (target.zoom - current.zoom) * alpha };
}
