export type WorldQuality='high'|'balanced'|'low';
export const QUALITY={high:{particles:900,traffic:18,sky:12},balanced:{particles:420,traffic:10,sky:7},low:{particles:100,traffic:4,sky:3}};
export const SEASONS=['Spring','Summer','Autumn','Winter'] as const;
export const WEATHER=['Sunny','Clear','Partly cloudy','Overcast','Light rain','Heavy rain','Snowfall','Light snow','Fog','Windy','Sunset','Night','Thunderclouds','Sunrise'] as const;
export function citySeed(city:string){let h=2166136261;for(const c of city)h=Math.imul(h^c.charCodeAt(0),16777619);return h>>>0;}
export function climateAt(city:string,seconds:number){
 const seed=citySeed(city),bucket=Math.floor(seconds/300),seasonIndex=((bucket+seed)%4+4)%4;
 const choices=seasonIndex===3?[6,7,8,1]:seasonIndex===1?[0,1,2,10,11,13]:seasonIndex===2?[3,4,5,9,12]:[0,2,4,8,9];
 const weatherIndex=choices[((Math.floor(bucket/4)+seed)%choices.length+choices.length)%choices.length];
 return {bucket,seasonIndex,season:SEASONS[seasonIndex],weather:WEATHER[weatherIndex],weatherIndex,night:weatherIndex===11,rain:[4,5,12].includes(weatherIndex),snow:[6,7].includes(weatherIndex),wind:weatherIndex===9?1:.25,transition:Math.min(1,(seconds-bucket*300)/12)};
}
/** Advance from authoritative snapshots with monotonic time; never trust the device wall clock for joined worlds. */
export class WorldClock {
 private server=0;private received=0;private sample:number|undefined;
 observe(serverSeconds:number|undefined,monotonicMs:number){if(serverSeconds!==undefined&&Number.isFinite(serverSeconds)&&serverSeconds!==this.sample){this.sample=serverSeconds;this.server=serverSeconds;this.received=monotonicMs;}}
 seconds(monotonicMs:number){return this.sample===undefined?0:this.server+Math.max(0,monotonicMs-this.received)/1000;}
}
export type RoadFeature={id:string;tags:Record<string,string>;points:number[][]};
export function trafficRoads(features:RoadFeature[]){return features.filter(f=>['residential','tertiary','secondary','primary','unclassified','service','living_street'].includes(f.tags.highway)&&!['private','no'].includes(f.tags.access)&&f.points.length>1).map(f=>({...f,length:f.points.slice(1).reduce((n,p,i)=>n+Math.hypot(p[0]-f.points[i][0],p[1]-f.points[i][1]),0)})).filter(f=>f.length>35);}
export function routePose(points:number[][],distance:number){
 let remaining=Math.max(0,distance);
 for(let i=1;i<points.length;i++){const a=points[i-1],b=points[i],length=Math.hypot(b[0]-a[0],b[1]-a[1]);if(!length)continue;if(remaining<=length||i===points.length-1){const t=Math.min(1,remaining/length);return {x:a[0]+(b[0]-a[0])*t,z:a[1]+(b[1]-a[1])*t,heading:Math.atan2(b[0]-a[0],b[1]-a[1]),end:i===points.length-1&&remaining>=length};}remaining-=length;}
 return {x:points[0]?.[0]||0,z:points[0]?.[1]||0,heading:0,end:true};
}

/** Continue only through connected mapped endpoints. Never draw a shortcut across a block. */
export function nextTrafficRoad(current:ReturnType<typeof trafficRoads>[number],roads:ReturnType<typeof trafficRoads>,choice:number){
 const end=current.points[current.points.length-1];
 const connected=roads.filter(r=>r.id!==current.id).flatMap(r=>{
  if(Math.hypot(r.points[0][0]-end[0],r.points[0][1]-end[1])<.1)return [r];
  const last=r.points[r.points.length-1];
  if(!['yes','1','true'].includes(r.tags.oneway)&&Math.hypot(last[0]-end[0],last[1]-end[1])<.1)return [{...r,points:[...r.points].reverse()}];
  return [];
 }).sort((a,b)=>a.id.localeCompare(b.id));
 return connected.length?connected[Math.abs(choice)%connected.length]:null;
}
