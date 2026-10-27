'use client';
import {useRef,useState} from 'react';
import {api,Data} from '../lib/api';
export default function EventTickets({event,onRefresh}:{event:Data;onRefresh:()=>Promise<void>}){
 const [review,setReview]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');const request=useRef(''),locked=useRef(false);const ticketing=event.ticketing;
 if(!ticketing?.price)return <p>Free admission</p>;
 if(ticketing.receipt?.refunded_at)return <p>✓ {ticketing.receipt.cost} PC refunded · Receipt {ticketing.receipt.id}</p>;
 if(!['scheduled','live'].includes(event.status))return <p>{ticketing.receipt?'Ticket receipt '+ticketing.receipt.id:'Ticket sales are closed.'}</p>;
 if(event.programme?.arena_booking_required&&!event.venue_booking)return <p>Ticket sales open after the organiser confirms the arena reservation.</p>;
 if(ticketing.entitled)return <p>✓ Ticket access confirmed {ticketing.receipt&&<small>· Receipt {ticketing.receipt.id}</small>}</p>;
 const approved=event.visibility==='public'||['approved','active'].includes(event.my_state);
 async function buy(){if(locked.current)return;locked.current=true;setBusy(true);setError('');request.current ||= crypto.randomUUID();try{await api(`/events/${event.id}/tickets`,'POST',{request_id:request.current,expected_cost:ticketing.price});await onRefresh();setReview(false);window.dispatchEvent(new Event('pulse-wallet-refresh'))}catch(e){setError((e as Error).message)}finally{locked.current=false;setBusy(false)}}
 return <section className="event-tickets"><b>{ticketing.price} PC per ticket · {ticketing.available} available</b>{!approved?<p>Request host approval before purchasing a private ticket.</p>:<button disabled={busy||!ticketing.available} onClick={()=>setReview(true)}>Review ticket purchase</button>}{review&&<div className="purchase-confirm" role="dialog" aria-label="Confirm event ticket"><p>{event.title} · {ticketing.price} Pulse Credits</p><p>Confirmed tickets reserve audience capacity. If the organiser cancels, the ticket price returns to your Credits wallet.</p><button disabled={busy} onClick={()=>setReview(false)}>Back</button><button disabled={busy} onClick={()=>void buy()}>{busy?'Confirming…':'Confirm ticket purchase'}</button></div>}{error&&<p role="alert">{error}</p>}</section>;
}
