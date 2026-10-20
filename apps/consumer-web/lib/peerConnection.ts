type Session={state?:string;event_id?:string;peer?:{id:string};members?:{id:string}[];requester?:string;target?:string};
/** Derived from authoritative consent/membership, never from layout or a timer. */
export function peerConnection(sessions:Session[],peerId?:string):'connected'|'pending'|null {
 if(!peerId)return null;
 const relevant=sessions.filter(s=>!s.event_id&&(s.peer?.id===peerId||s.members?.some(p=>p.id===peerId)||s.requester===peerId||s.target===peerId));
 return relevant.some(s=>s.state==='accepted')?'connected':relevant.some(s=>s.state==='pending')?'pending':null;
}
