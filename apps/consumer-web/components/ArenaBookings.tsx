'use client';
import {useEffect,useState} from 'react';
import {api,Data} from '../lib/api';
export default function ArenaBookings(){
 const [open,setOpen]=useState(false),[rows,setRows]=useState<Data[]|null>(null),[error,setError]=useState('');
 useEffect(()=>{if(!open)return;let active=true;setError('');api('/venue-reservations/mine').then(data=>{if(active)setRows(data)}).catch(e=>{if(active)setError(e.message)});return()=>{active=false}},[open]);
 return <details onToggle={e=>setOpen(e.currentTarget.open)}><summary>My Grand Arena bookings</summary>{error&&<p role="alert">{error}</p>}{!rows&&!error&&<p>Loading reservations…</p>}{rows?.length===0&&<p>Your confirmed bookings will appear here.</p>}{rows?.map(b=><article className="record" key={b.id}><b>{b.event_title}</b><p>{b.city} · {b.hours} hours · {b.cost} PC · {b.refunded?'Refunded':b.status}</p><p>{new Date(b.starts_at*1000).toISOString().replace('T',' ').slice(0,16)} UTC</p><small>Receipt {b.id}</small><button onClick={()=>window.dispatchEvent(new CustomEvent('pulse-open-event',{detail:b.event_id}))}>View event and receipt</button></article>)}</details>;
}
