type State=Record<string,any>;
// A server transition supersedes all movement sent before it began. Keep its
// barrier after completion: either transport may deliver an old reply later.
export class MotionTransition {
 paused=false;
 private supersededThrough=0;
 begin(sequence:number){if(this.paused)return false;this.paused=true;this.supersededThrough=Math.max(this.supersededThrough,sequence);return true}
 finish(){this.paused=false}
 accepts(sequence:unknown){return typeof sequence!=='number'||sequence>this.supersededThrough}
}
export function acceptMotion(current:State|null,result:State,city:string,zone:string):State|null {
 if(!current||current.city!==city||current.position?.zone_id!==zone)return current;
 const position=result.position;
 if(!position||position.last_move<(current.position?.last_move||0))return current;
 const incoming=result.movement_config||position.movement_config;
 const policy=incoming&&incoming.version>=(current.movement_config?.version??-1)?incoming:current.movement_config;
 return {...current,...result,position,movement_config:policy};
}
export function acceptSnapshot(current:State|null,next:State):State {
 if(current?.movement_config&&(!next.movement_config||next.movement_config.version<current.movement_config.version))next={...next,movement_config:current.movement_config};
 if(current&&current.city===next.city&&current.server_time&&next.server_time&&next.server_time<current.server_time)return current;
 if(current&&current.city===next.city&&(current.position?.last_move||0)>(next.position?.last_move||0))
  return {...next,position:current.position,rental:current.rental,scene:current.scene,journey:current.journey};
 return next;
}
export class MotionStall {
 since=0;
 update(blocked:boolean,now:number){if(!blocked){this.since=0;return false}this.since ||= now;return now-this.since>=2500}
}
