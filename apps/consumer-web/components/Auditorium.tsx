'use client';
import GiftControls from './GiftControls';
import {useEffect,useRef,useState} from 'react';
import {api,Data} from '@/lib/api';
export default function Auditorium({event,onRefresh,inside=false}:{event:Data;inside?:boolean;onRefresh:()=>Promise<void>}){
 const [activity,setActivity]=useState<Data>({}),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[gift,setGift]=useState('');const pending=useRef<{id:string;gift:string;expected_cost:number}|null>(null);
 useEffect(()=>{if(!event.joined||event.status!=='live')return;const load=()=>api(`/events/${event.id}/activity`).then(setActivity).catch(()=>{});load();const t=setInterval(load,4000);return()=>clearInterval(t)},[event.id,event.joined,event.status]);
 const run=async(path:string,body:Data={})=>{setBusy(true);try{await api(path,'POST',body);setMessage('');window.dispatchEvent(new Event('pulse-wallet-refresh'));await onRefresh();return true}catch(e){setMessage((e as Error).message);return false}finally{setBusy(false)}};
 if(event.venue_experience_type!=='auditorium'||inside)return null;
 return <section className="auditorium-controls"><p className="eyebrow">🎭 MINDAAM LIVE AUDITORIUM</p><p>Stage, audience and your people — inside the world.</p>{event.joined&&event.status==='live'&&<><button className="primary" disabled={busy} onClick={async()=>{if(await run(`/events/${event.id}/venue/enter`))window.dispatchEvent(new Event('pulse-venue-entered'))}}>Enter auditorium</button><GiftControls contextType="event" contextId={event.id}/><p>{event.participants?.filter((p:Data)=>p.friend).length||0} friends attending</p>{event.participants?.filter((p:Data)=>p.friend).map((p:Data)=><span className="pill" key={p.id}>{p.username}</span>)}{event.can_manage&&<label className="check"><input type="checkbox" checked={event.chat_enabled} onChange={async e=>{try{await api(`/events/${event.id}/chat`,'PUT',{enabled:e.target.checked});await onRefresh()}catch(e){setMessage((e as Error).message)}}}/>Event chat enabled</label>}<p>Use the existing communication controls for Minimise, Expand and Full Screen.</p></>}{message&&<p role="alert">{message}</p>}</section>
}
