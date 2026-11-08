import {useId} from 'react';
/** Draw a miniature axonometric view of the selected mapped footprint. */
export default function PropertyPreview({points,colors,name}:{points:number[][];colors:Record<string,string>;name:string}){
 const id=useId();
 if(points.length<3)return null;
 const cx=points.reduce((n,p)=>n+p[0],0)/points.length,cz=points.reduce((n,p)=>n+p[1],0)/points.length;
 const raw=points.map(([x,z])=>[(x-cx)-(z-cz),((x-cx)+(z-cz))*.48]);
 const extent=Math.max(1,...raw.flatMap(([x,y])=>[Math.abs(x)/100,Math.abs(y)/34]));
 const ring=raw.map(([x,y])=>[146+x/extent,83+y/extent]);
 const roof=ring.map(([x,y])=>[x,y-29]);
 const faces=ring.slice(1).map(([x,y],i)=>({depth:(y+ring[i][1])/2,points:[ring[i],[x,y],roof[i+1],roof[i]]})).sort((a,b)=>a.depth-b.depth);
 return <svg role="img" aria-label={'Mapped footprint preview of '+name} viewBox="0 0 292 138" style={{width:'100%',height:'auto',maxHeight:170,borderRadius:12}}>
 <defs><pattern id={id} width="18" height="18" patternUnits="userSpaceOnUse"><path d="M0 18L18 0M0 0L18 18" fill="none" stroke="#789aa8" strokeOpacity=".16" strokeWidth=".6"/></pattern></defs>
 <rect width="292" height="138" fill="#18323a"/><rect width="292" height="138" fill={'url(#'+id+')'}/>
 {faces.map((f,i)=><polygon key={i} points={f.points.map(p=>p.join(',')).join(' ')} fill={colors.wall||'#b89a7d'} stroke="#544b46" strokeWidth=".6"/>)}
 <polygon points={roof.map(p=>p.join(',')).join(' ')} fill={colors.roof||'#c6cebd'} stroke="#515e59" strokeWidth="1"/>
 </svg>;
}
