'use client';
import {useEffect,useState} from 'react';
import {Radio,CalendarDays,X} from 'lucide-react';
import {Data} from '../lib/api';
export default function CityPulse({world,userId}:{world:Data|null;userId?:string}){
 const [open,setOpen]=useState(false),[dismissed,setDismissed]=useState<string[]>([]);
 useEffect(()=>{if(userId)try{setDismissed(JSON.parse(sessionStorage.getItem('mindaam-event-dismissed:'+userId)||'[]'))}catch{}},[userId]);
 if(!userId||!world||world.scene||world.journey)return null;
 const events=world.arena?.events||[],live=events.find((e:Data)=>e.status==='live'&&!dismissed.includes(e.id));
 function dismiss(id:string){const next=[...dismissed,id].slice(-100);setDismissed(next);try{sessionStorage.setItem('mindaam-event-dismissed:'+userId,JSON.stringify(next))}catch{}}
 return <aside className="city-pulse"><button aria-expanded={open} onClick={()=>setOpen(!open)}><Radio size={17}/>City Pulse{live&&<span className="pulse-live">Live</span>}</button>{open&&<section><header><b>What’s happening</b><button aria-label="Close City Pulse" onClick={()=>setOpen(false)}><X size={18}/></button></header><p>{world.online??0} explorers in this district</p>{live&&<article><b>Live at Grand Arena</b><p>{live.title}</p><button onClick={()=>window.dispatchEvent(new CustomEvent('pulse-open-event',{detail:live.id}))}>View event</button><button onClick={()=>dismiss(live.id)}>Dismiss reminder</button></article>}{events.filter((e:Data)=>e.status!=='live').map((e:Data)=><button key={e.id} onClick={()=>window.dispatchEvent(new CustomEvent('pulse-open-event',{detail:e.id}))}><CalendarDays size={16}/>{e.title}<small>{new Date(e.starts_at*1000).toLocaleString()}</small></button>)}{!events.length&&<p>No scheduled arena events yet.</p>}<button onClick={()=>window.dispatchEvent(new CustomEvent('pulse-open-event',{detail:''}))}>Browse events · Book Grand Arena</button>{world.transit?.hub&&<button onClick={()=>window.dispatchEvent(new CustomEvent('pulse-city-action',{detail:{kind:'transit'}}))}>View transport departures</button>}<p>{world.collectibles?.length||0} nearby collectible opportunities</p></section>}</aside>;
}
