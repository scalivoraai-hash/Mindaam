'use client';
import {useEffect,useState} from 'react';
import {Data} from '../lib/api';
import {WorldClock} from '../lib/worldClimate';
export default function EventWelcome({event}:{event:Data}){
 const [clock]=useState(()=>new WorldClock()),[now,setNow]=useState(0);
 useEffect(()=>{clock.observe(event.server_time,performance.now());setNow(clock.seconds(performance.now()))},[clock,event.server_time]);
 useEffect(()=>{const timer=setInterval(()=>setNow(clock.seconds(performance.now())),1000);return()=>clearInterval(timer)},[clock]);
 if(!['scheduled','live'].includes(event.status))return null;
 const left=Math.max(0,Math.floor(event.starts_at-now));const presenter=event.participants?.find((p:Data)=>p.id===event.presentation?.presenter_id)||event.participants?.find((p:Data)=>p.role==='host');
 return <div className="event-welcome"><small>{event.status==='live'?'WELCOME TO THE SHOW':'YOUR NEXT SHARED EXPERIENCE'}</small><p>{event.status==='live'?`${presenter?.username||event.organiser?.name||'Your host'} welcomes you to ${event.title}`:left>0?`Starts in ${Math.floor(left/3600)}h ${Math.floor(left%3600/60)}m ${left%60}s`:'Waiting for the organiser to begin'}</p>{event.venue_experience_type==='auditorium'&&event.programme?.arena_booking_required&&!event.venue_booking&&<small>Arena reservation pending</small>}</div>;
}
