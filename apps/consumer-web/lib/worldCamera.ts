/** A spherical orbit keeps vertical pitch independent of camera-relative walking. */
export function orbitOffset(angle:number,pitch:number,distance:number){const elevation=Math.max(.08,Math.min(1.48,pitch)),radius=Math.max(5,Math.min(75,distance)),horizontal=Math.cos(elevation)*radius;return {x:Math.sin(angle)*horizontal,y:Math.sin(elevation)*radius,z:Math.cos(angle)*horizontal}}

/** Look into the room so the local avatar does not cover the distant stage. */
export function indoorFocus(position:{x:number;y:number;z:number},angle:number,back=-15){
 return {x:Math.max(-10,Math.min(10,position.x-Math.sin(angle)*6)),y:position.y+1.7,z:Math.max(back+3,Math.min(13.8,position.z-Math.cos(angle)*6))};
}

/** Shorten an indoor orbit along its original ray, preserving the viewing pitch. */
export function indoorOrbit(focus:{x:number;y:number;z:number},desired:{x:number;y:number;z:number},back=-15){
 let fraction=1;
 for(const [axis,min,max] of [['x',-10.5,10.5],['y',.5,7.7],['z',back+.5,14.3]] as const){
  const delta=desired[axis]-focus[axis];
  if(delta>0)fraction=Math.min(fraction,(max-focus[axis])/delta);
  else if(delta<0)fraction=Math.min(fraction,(min-focus[axis])/delta);
 }
 fraction=Math.max(0,fraction);
 return {x:focus.x+(desired.x-focus.x)*fraction,y:focus.y+(desired.y-focus.y)*fraction,z:focus.z+(desired.z-focus.z)*fraction};
}

/** An angle-independent pivot fits the full orbit in the room. Drag never changes radius. */
export function stableIndoorOrbit(position:{x:number;y:number;z:number},angle:number,pitch:number,zoom:number,back=-15){
 const radius=Math.max(6,Math.min(10,zoom)),y=position.y+1.7;
 const elevation=Math.max(.08,Math.min(pitch,Math.asin(Math.min(1,(7.5-y)/radius))));
 // Reserve the entire horizontal circle, independent of pitch as well as yaw.
 const focus={x:Math.max(-10.5+radius,Math.min(10.5-radius,position.x)),y,z:Math.max(back+.5+radius,Math.min(14.3-radius,position.z-6))};
 const offset=orbitOffset(angle,elevation,radius);
 return {focus,position:{x:focus.x+offset.x,y:focus.y+offset.y,z:focus.z+offset.z}};
}
