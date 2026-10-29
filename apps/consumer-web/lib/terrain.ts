/** Server-classified OSM coverage. Preview only: this never grants rewards or authority. */
export type TerrainFeature={kind:string;points:number[][];holes:number[][][]};
export type Navigation={radius:number;features:TerrainFeature[]};
export function inside(x:number,z:number,p:number[][]){let hit=false;for(let i=0,j=p.length-1;i<p.length;j=i++){const a=p[i],b=p[j];if((a[1]>z)!==(b[1]>z)&&x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0])hit=!hit;}return hit;}
function distance(x:number,z:number,a:number[],b:number[]){const dx=b[0]-a[0],dz=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz||1)));return Math.hypot(x-a[0]-t*dx,z-a[1]-t*dz);}
export function terrainNavigator(nav:Navigation){
 const grid=new Map<string,TerrainFeature[]>(),lo=Math.floor(-nav.radius/32),hi=Math.floor(nav.radius/32);
 for(const f of nav.features){if(!f.points.length)continue;const pad=f.kind==='road'?6:.35,x=f.points.map(p=>p[0]),z=f.points.map(p=>p[1]);for(let ix=Math.max(lo,Math.floor((Math.min(...x)-pad)/32));ix<=Math.min(hi,Math.floor((Math.max(...x)+pad)/32));ix++)for(let iz=Math.max(lo,Math.floor((Math.min(...z)-pad)/32));iz<=Math.min(hi,Math.floor((Math.max(...z)+pad)/32));iz++){const key=ix+':'+iz,list=grid.get(key)||[];list.push(f);grid.set(key,list);}}
 const permits=(x:number,z:number)=>{
  if(!Number.isFinite(x)||!Number.isFinite(z)||Math.abs(x)>nav.radius||Math.abs(z)>nav.radius)return false;
  let allowed=true;
  for(const f of grid.get(Math.floor(x/32)+':'+Math.floor(z/32))||[]){const p=f.points,closed=p.length>=4&&p[0][0]===p[p.length-1][0]&&p[0][1]===p[p.length-1][1],contains=closed&&inside(x,z,p)&&!f.holes.some(h=>inside(x,z,h)),near=p.slice(1).some((b,i)=>distance(x,z,p[i],b)<=(f.kind==='road'?6:.35));if(['blocked','building','barrier'].includes(f.kind)&&((near&&f.kind!=='building')||contains&&['blocked','building'].includes(f.kind)))return false;allowed ||= f.kind==='road'&&near||f.kind==='public'&&contains;}
  return allowed;
 };
 const grass=(x:number,z:number)=>permits(x,z)&&!(grid.get(Math.floor(x/32)+':'+Math.floor(z/32))||[]).some(f=>f.kind==='road'&&f.points.slice(1).some((b,i)=>distance(x,z,f.points[i],b)<6.3));
 return {permits,grass,step(x:number,z:number,dx:number,dz:number){const count=Math.max(1,Math.ceil(Math.hypot(dx,dz)/.2)),sx=dx/count,sz=dz/count;for(let i=0;i<count;i++){if(permits(x+sx,z+sz)){x+=sx;z+=sz;}else{for(const [ax,az] of [[sx,0],[0,sz]].sort((a,b)=>Math.hypot(...b as [number,number])-Math.hypot(...a as [number,number]))){if((ax||az)&&permits(x+ax,z+az)){x+=ax;z+=az;break;}}}}return {x,z};}};
}
