'use client';
import {destinationCountry} from '@/lib/destinationFlag';
import CountryFlag from '@/components/CountryFlag';
import WorldLoading from '@/components/WorldLoading';
import {loadGeography} from '@/lib/geographyCache';
import {MOVEMENT} from '@/lib/movement';
import {useEffect,useState} from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import {api,Data} from '@/lib/api';
const World=dynamic(()=>import('@/components/World'),{ssr:false,loading:()=> <WorldLoading/>});
export default function Explore(){
 const [cities,setCities]=useState<Data[]>([]);useEffect(()=>{const refresh=()=>api('/cities').then(d=>setCities(d.filter((c:Data)=>c.enabled&&c.public!==false&&c.joinable!==false))).catch(()=>{});refresh();const timer=setInterval(refresh,15000);return()=>clearInterval(timer)},[]);
 const [city,setCity]=useState('milton-keynes'),[world,setWorld]=useState<Data|null>(null),[error,setError]=useState(''),[geometry,setGeometry]=useState<Data|null>(null);
 useEffect(()=>{let active=true;setWorld(null);setError('');Promise.all([api('/world-preview/'+city),loadGeography(city)]).then(([v,g])=>{if(active){setWorld(v);setGeometry(g)}}).catch(e=>{if(active)setError(e.message)});return()=>{active=false}},[city]);
 const move=(dx:number,dz:number)=>setWorld(w=>{if(!w)return w;const x=w.position.x+dx*MOVEMENT.previewStep,z=w.position.z+dz*MOVEMENT.previewStep;const valid=geometry?.features.some((f:Data)=>f.tags.highway&&f.points.slice(1).some((b:number[],i:number)=>{const a=f.points[i],vx=b[0]-a[0],vz=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*vx+(z-a[1])*vz)/(vx*vx+vz*vz||1)));return Math.hypot(x-a[0]-t*vx,z-a[1]-t*vz)<=6}));return valid?{...w,position:{x:Math.max(-(geometry?.radius||350),Math.min(geometry?.radius||350,x)),z:Math.max(-(geometry?.radius||350),Math.min(geometry?.radius||350,z))}}:w});
 return <main style={{position:'relative',height:'100dvh',overflow:'hidden',background:'#132b2b'}}><World world={world} onMove={move}/><section className="preview-card" style={{position:'absolute',top:24,left:24,width:'min(290px,calc(100vw - 48px))',padding:16,borderRadius:20,background:'rgba(12,29,30,.94)',border:'1px solid #496459',color:'#edf3e5'}}><Link href="/" style={{fontWeight:800,color:'#c3ff68',letterSpacing:3}}>MyLilWorlds</Link><h1 style={{fontSize:26,margin:'18px 0 10px'}}>Explore the district</h1><p style={{fontSize:16,lineHeight:1.5}}>Explore a stylised real neighbourhood before you join. Sign in to meet players, collect items and earn rewards.</p><label htmlFor="preview-city">City</label><select id="preview-city" value={city} onChange={e=>setCity(e.target.value)} style={{width:'100%',margin:'8px 0 16px'}}>{cities.map(c=><option key={c.id} value={c.id}>{c.id===city?'✓ '+destinationCountry(c)+' '+c.name:destinationCountry(c)+' '+c.name+' · Explore Now'}</option>)}</select><div className="destination-online">{(cities.find(c=>c.id===city)?.online??0)>0?<><b>{cities.find(c=>c.id===city)?.online}</b><span>PEOPLE EXPLORING NOW</span></>:<span>Be the first explorer here</span>}</div><p style={{fontSize:14,color:'#b5c9bd'}}>OpenStreetMap district · Stylised buildings<br/>Use WASD or touch to explore. Drag to look.</p>{error&&<p role="alert">{error} <button onClick={()=>location.reload()}>Retry</button></p>}{!world&&!error&&<p role="status">Loading district…</p>}<Link href="/" className="primary" style={{display:'inline-block',marginTop:12}}>Create an account to play</Link></section></main>
}
