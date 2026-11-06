'use client';
import {useEffect,useRef,useState} from 'react';
import {api,type Data} from '@/lib/api';
import PropertyPreview from './PropertyPreview';
import {openUserProfile} from './UserProfile';
import styles from './PropertyDesk.module.css';

export default function PropertyDesk({city,selected,onWallet,onExplore,onVisit}:{city:string;selected?:string;onWallet:()=>void;onExplore:()=>void;onVisit:(w:Data)=>void}){
 const [browseCity,setBrowseCity]=useState(city),[cities,setCities]=useState<Data[]>([]);
 useEffect(()=>{api('/cities').then(rows=>setCities(rows.filter((c:Data)=>c.enabled&&c.public&&c.joinable))).catch(e=>setMessage(e.message))},[]);
 const [tab,setTab]=useState('Nearby'),[rows,setRows]=useState<Data[]>([]),[item,setItem]=useState<Data|null>(null);
 const [xp,setXP]=useState(0),[confirming,confirm]=useState(false),[won,setWon]=useState(false);
 const [version,refresh]=useState(0),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 const [since,setSince]=useState(''),[status,setStatus]=useState('all');
 const [filter,setFilter]=useState(''),[page,setPage]=useState(0);
 const [draftColors,setDraftColors]=useState<Record<string,string>>({});
 const key=useRef(''),lock=useRef(false);
 async function open(id:string){
   const d=await api('/properties/detail/'+encodeURIComponent(id));setItem(d);setDraftColors(d.style.colors||{});setXP(d.balance);
   confirm(false);setWon(false);setMessage('');key.current=crypto.randomUUID();
 }
 useEffect(()=>{if(selected)open(selected).catch(e=>setMessage(e.message))},[selected]);
 useEffect(()=>{let current=true;
   const path=tab==='Nearby'?'city/'+browseCity+'?offset='+page*48:tab==='Portfolio'?'portfolio':tab==='Offers'?'offers':tab==='Achievements'?'achievements':'history';
   api('/properties/'+path).then(d=>{if(current){setRows(d.items||d);if(typeof d.balance==='number')setXP(d.balance)}}).catch(e=>{if(current)setMessage(e.message)});
   return()=>{current=false};
 },[browseCity,tab,page,version]);
 async function run(fn:()=>Promise<void>){if(lock.current)return;lock.current=true;setBusy(true);setMessage('');
   try{await fn();refresh(n=>n+1)}catch(e){setMessage((e as Error).message)}finally{lock.current=false;setBusy(false)}
 }
 const form=(e:React.FormEvent<HTMLFormElement>)=>{e.preventDefault();return new FormData(e.currentTarget)};
 return <section className={styles.desk} aria-busy={busy}>
 <nav aria-label="My Properties">{['Nearby','Portfolio','Offers','History','Achievements'].map(t=><button key={t} aria-pressed={tab===t&&!item} onClick={()=>{setTab(t);setItem(null);setFilter('');setPage(0);setMessage('')}}>{t}</button>)}</nav>
 {message&&<p role="status">{message}</p>}
 {item?<article key={item.id}><PropertyPreview name={item.name} points={item.outline||[]} colors={draftColors}/><small>{item.district} · {item.city} · {item.category}</small><h3>{item.name}</h3>
 <p>{item.mine?'Your property':item.owned?'🏡 This property has an owner':item.enabled?'Available':'Reserved'}{item.owner?' · '+item.owner:''}</p>
 <p>Spendable balance <b>{xp.toLocaleString()} XP</b></p>
 {won&&<div role="status"><strong>🎉 Congratulations! You’re now a property owner!</strong><p>Your new property is ready. Give it a name, customise it and make it yours!</p></div>}
 {!item.owned&&item.enabled&&(xp<item.price?<><h4>🔒 Just a little more XP!</h4><p>You need another {(item.price-xp).toLocaleString()} XP to claim this property.</p><button onClick={onExplore}>Earn more XP</button><button onClick={()=>setItem(null)}>Explore nearby properties</button></>:
 <><h4>{item.price.toLocaleString()} XP</h4>{confirming?<><p>After this purchase you’ll have {(xp-item.price).toLocaleString()} XP.</p>
 <button disabled={busy} onClick={()=>run(async()=>{
   const result=await api('/properties/'+item.id+'/claim','POST',{amount:item.price,request_key:key.current});
   setXP(result.balance);onWallet();await open(item.id);setWon(true);
 })}>Confirm purchase</button><button onClick={()=>confirm(false)}>Cancel</button></>:<button className="primary" disabled={!item.enabled} onClick={()=>confirm(true)}>🏡 MAKE IT MINE</button>}</>)}
 {item.mine&&<form onSubmit={e=>{const f=form(e);run(async()=>{const result=await api('/properties/'+item.id+'/studio','PATCH',{
 name:f.get('name'),board:f.get('board'),description:f.get('description'),access:f.get('access'),
 colors:Object.fromEntries(['wall','roof','trim','door','window'].filter(k=>f.get(k)).map(k=>[k,f.get(k)])),guests:String(f.get('guests')||'').split(',').map(s=>s.trim()).filter(Boolean)});setItem({...item,...result});setMessage('Property published.')})}}>
 <h4>Property Studio</h4><label>Name my property<input name="name" required minLength={2} maxLength={48} defaultValue={item.name}/></label>
 <label>Nameboard<select name="board" defaultValue={item.style.board||'navy'}><option>navy</option><option>forest</option><option>burgundy</option></select></label>
 {['wall','roof','trim','door','window'].map(part=><label key={part}>{part} colour<select name={part} onChange={e=>setDraftColors({...draftColors,[part]:e.target.value})} defaultValue={item.style.colors?.[part]||''}><option value="">Original finish</option>{Object.entries({'Sand':'#e9dcc7','Terracotta':'#bd8d74','Forest':'#234e51','Slate':'#405670','Ivory':'#f0eedc','Plum':'#634854'}).map(([n,c])=><option key={c} value={c}>{n}</option>)}</select></label>)}
 <label>Description<textarea name="description" maxLength={220} defaultValue={item.style.description}/></label>
 <label>Access<select name="access" defaultValue={item.style.access||'private'}>{['private','friends','invite','public'].map(a=><option key={a}>{a}</option>)}</select></label>
 <label>Invited explorer IDs<input name="guests" defaultValue={(item.style.guests||[]).join(', ')}/></label>
 <button disabled={busy} className="primary">Save and publish</button></form>}
 {item.owned&&!item.mine&&item.resale&&<button disabled={busy} onClick={()=>run(async()=>{await api('/properties/'+item.id+'/request','POST',{});setMessage('Purchase request delivered.')})}>Request to purchase</button>}
 {item.owned&&!item.mine&&item.resale&&<form onSubmit={e=>{const f=form(e);run(async()=>{await api('/properties/'+item.id+'/offer','POST',{amount:Number(f.get('amount'))});setMessage('Offer delivered to the owner.')})}}>
 <label>Your XP offer<input type="number" name="amount" min="1" max={xp} required/></label><button disabled={busy}>Make an XP offer</button></form>}
 {item.owner&&<button onClick={()=>openUserProfile(item.owner_id)}>View owner profile</button>}
 {item.owned&&<button disabled={busy} onClick={()=>run(async()=>onVisit(await api('/places/travel/visit','POST',{city:item.city,place_id:'property:'+item.id})))}>Visit property</button>}
 {item.may_enter&&<button disabled={busy} onClick={()=>run(async()=>{await api('/buildings/home:'+item.id+'/enter','POST',{});onVisit(await api('/world/'+item.city))})}>Enter property</button>}
 {item.category==='venue'&&item.mine&&<button onClick={()=>window.dispatchEvent(new Event('mindaam-property-host'))}>Organise an event</button>}
 <small>Ownership grants a virtual entitlement inside Mindaam. XP has no cash value.</small></article>:
 <>{tab==='Nearby'&&<label>Explore properties by city<select value={browseCity} onChange={e=>{setBrowseCity(e.target.value);setRows([]);setPage(0)}}>{cities.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}{(tab==='Nearby'||tab==='Portfolio')&&<label>Find a property<input type="search" value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Name, city or category"/></label>}
 {(tab==='Nearby'||tab==='Portfolio')&&<div className={styles.filters}><label>Status<select value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All</option><option value="owned">Owned</option><option value="available">Available</option><option value="reserved">Reserved</option></select></label>{tab==='Portfolio'&&<label>Acquired since<input type="date" value={since} onChange={e=>setSince(e.target.value)}/></label>}</div>}
 {rows.filter(r=>(tab!=='Portfolio'||!since||r.acquired*1000>=Date.parse(since))&&(!['Portfolio','Nearby'].includes(tab)||status==='all'||status===(r.owned?'owned':r.enabled?'available':'reserved'))).filter(r=>[r.name,r.city,r.category].join(' ').toLowerCase().includes(filter.toLowerCase())).map(r=>
 tab==='Offers'?<article key={r.id}><b>{r.amount} XP</b><p>{r.property_id} · {r.state} · {r.incoming?'Incoming':'Outgoing'}</p>
 {((r.state==='pending'&&r.incoming)||(r.state==='countered'&&!r.incoming))&&<form onSubmit={e=>{const f=form(e);const action=(e.nativeEvent as SubmitEvent).submitter?.getAttribute('value');run(async()=>{await api('/properties/offers/'+r.id,'POST',{action,expected_amount:r.amount,amount:action==='counter'?Number(f.get('counter')):null});onWallet()})}}>
 <button value="accept" disabled={busy}>Accept</button><button value="reject" disabled={busy}>Reject</button>{r.incoming&&<><input type="number" min="1" aria-label="Counteroffer XP" name="counter"/><button value="counter" disabled={busy}>Counteroffer</button></>}</form>}</article>:
 tab==='Achievements'?<article key={r.name}><b>{r.earned?'🏅 ':''}{r.name}</b><small>{r.progress} / {r.goal}</small></article>:tab==='History'?<article key={r.id}><b>{r.action} · {r.xp} XP</b><small>{r.property_id} · {new Date(r.date*1000).toLocaleDateString()}</small></article>:
 <button className={styles.card} data-property-id={r.id} key={r.id} onClick={()=>run(()=>open(r.id))}><strong>{r.name}</strong><span>{r.city} · {r.category}</span><b>{r.owned?'Owned':r.enabled?r.price.toLocaleString()+' XP':'Reserved'}</b>{r.mine&&<small>{r.cost.toLocaleString()} XP · {new Date(r.acquired*1000).toLocaleDateString()}</small>}</button>)}
 {!rows.length&&<p>No {tab==='Portfolio'?'owned properties':tab.toLowerCase()+' records'} yet.</p>}
 {tab==='Nearby'&&<nav><button disabled={!page} onClick={()=>setPage(page-1)}>Previous</button><button disabled={rows.length<48} onClick={()=>setPage(page+1)}>Next</button></nav>}</>}
 </section>;
}
