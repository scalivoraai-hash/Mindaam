'use client';
import {useEffect,useState} from 'react';
import {api,type Data} from '@/lib/api';
export const propertyTabs:Record<string,string>={'Property overview':'overview','All properties':'inventory','City XP pricing':'prices','Property ownership':'owners','Trading history':'trades','Offers and transfers':'offers','Venue licences':'venues','Property permissions':'settings','Property audit logs':'audit'};
function AdminRecords({kind}:{kind:string}){
 const [page,setPage]=useState(0),[rows,setRows]=useState<Data[]>([]),[msg,setMsg]=useState('');
 useEffect(()=>{let active=true;api('/properties/admin/records/'+kind+'?offset='+page*50).then(d=>{if(active)setRows(d)}).catch(e=>{if(active)setMsg(e.message)});return()=>{active=false}},[kind,page]);
 return <section><p role="status">{msg}</p>{rows.map((r,i)=><details key={i}><summary>{r.name||r.property_id||r.target||r.id||r.scope} · {r.category||r.state||r.action||r.amount}</summary><dl>{Object.entries(r).map(([k,v])=><div key={k}><dt>{k}</dt><dd>{typeof v==='object'?JSON.stringify(v):String(v??'—')}</dd></div>)}</dl>{kind==='inventory'&&<button onClick={async()=>{const category=prompt('Property category',r.category);if(!category)return;try{await api('/properties/admin/inventory/'+r.id,'PATCH',{category,resale:confirm('Allow resale of this property?')});setMsg('Inventory controls saved.')}catch(e){setMsg((e as Error).message)}}}>Edit inventory controls</button>}{kind==='trades'&&<><button onClick={async()=>{const reason=prompt('Reason for requesting a reversal (at least 12 characters)');if(!reason)return;try{await api('/properties/admin/trades/'+r.id+'/review','POST',{reason});setMsg('Reversal requested.')}catch(e){setMsg((e as Error).message)}}}>Request reversal</button><button onClick={async()=>{if(!confirm('Approve the requested XP and entitlement reversal?'))return;try{await api('/properties/admin/trades/'+r.id+'/reverse','POST',{});setMsg('Reversal applied.')}catch(e){setMsg((e as Error).message)}}}>Approve reversal</button></>}</details>)}{!rows.length&&<p>No records.</p>}<button disabled={!page} onClick={()=>setPage(page-1)}>Previous</button><button disabled={rows.length<50} onClick={()=>setPage(page+1)}>Next</button></section>
}
function PolicyEditor(){
 const [settings,setSettings]=useState<Data|null>(null),[msg,setMsg]=useState('');
 useEffect(()=>{api('/properties/admin/policy').then(setSettings).catch(e=>setMsg(e.message))},[]);
 return <section><p role="status">{msg}</p>{settings&&<form onSubmit={async e=>{e.preventDefault();try{await api('/properties/admin/policy','PUT',settings);setMsg('Settings saved.')}catch(e){setMsg((e as Error).message)}}}>{['purchase','resale'].map(k=><label key={k}><input type="checkbox" checked={settings[k]} onChange={e=>setSettings({...settings,[k]:e.target.checked})}/>{k} enabled</label>)}{['minimum_xp','hourly_claims'].map(k=><label key={k}>{k.replace('_',' ')}<input type="number" value={settings[k]} onChange={e=>setSettings({...settings,[k]:Number(e.target.value)})}/></label>)}<button>Save settings</button></form>}</section>
}

export default function PropertyEconomyAdmin({tab}:{tab:string}){
 const [cities,setCities]=useState<Data[]>([]),[totals,setTotals]=useState<Data>({}),[msg,setMsg]=useState(''),[rev,setRev]=useState(0);
 useEffect(()=>{Promise.all([api('/properties/admin/coverage'),api('/properties/admin/overview')]).then(([c,t])=>{setCities(c);setTotals(t)}).catch(e=>setMsg(e.message))},[rev]);
 if(tab==='settings')return <PolicyEditor/>;
 if(!['overview','prices','venues'].includes(tab))return <AdminRecords kind={tab} key={tab}/>;
 return <section><p role="status">{msg}</p>{tab!=='overview'&&<AdminRecords kind={tab}/>}<dl>{Object.entries(totals).map(([k,v])=><div key={k}><dt>{k.replace('_',' ')}</dt><dd>{String(v)}</dd></div>)}</dl>
 <form onSubmit={async e=>{e.preventDefault();const f=new FormData(e.currentTarget);try{await api('/properties/admin/prices','PUT',{scope:f.get('scope'),category:f.get('category'),amount:Number(f.get('xp')),enabled:f.get('enabled')==='on'});setMsg('Price rule saved.')}catch(e){setMsg((e as Error).message)}}}>
 <h3>XP pricing</h3><label>City, country code, property ID or global (*)<input name="scope" required list="property-city-scopes"/></label><datalist id="property-city-scopes">{cities.map(c=><option key={c.city} value={c.city}/>)}</datalist>
 <label>Category<select name="category">{['house','apartments','townhouse','villa','residential','office','shop','commercial','building','venue'].map(c=><option key={c}>{c}</option>)}</select></label>
 <label>XP price<input name="xp" type="number" min="1" max="1000000000" required/></label><label><input type="checkbox" name="enabled" defaultChecked/>Purchases enabled</label><button>Save pricing</button></form>
 <h3>City inventory</h3><table><thead><tr><th>City</th><th>Eligible</th><th>Registered</th><th>Inventory</th></tr></thead><tbody>{cities.map(c=><tr key={c.city}><td>{c.city}</td><td>{c.eligible}</td><td>{c.registered}</td><td><button onClick={async()=>{try{await api('/properties/admin/register/'+c.city,'POST',{});setRev(v=>v+1)}catch(e){setMsg((e as Error).message)}}}>Register</button></td></tr>)}</tbody></table></section>;
}
