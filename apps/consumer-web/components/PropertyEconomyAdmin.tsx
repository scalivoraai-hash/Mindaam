'use client';
import {useEffect,useState} from 'react';
import {api,type Data} from '@/lib/api';
export default function PropertyEconomyAdmin(){
 const [cities,setCities]=useState<Data[]>([]),[totals,setTotals]=useState<Data>({}),[msg,setMsg]=useState(''),[rev,setRev]=useState(0);
 useEffect(()=>{Promise.all([api('/properties/admin/coverage'),api('/properties/admin/overview')]).then(([c,t])=>{setCities(c);setTotals(t)}).catch(e=>setMsg(e.message))},[rev]);
 return <section><p role="status">{msg}</p><dl>{Object.entries(totals).map(([k,v])=><div key={k}><dt>{k.replace('_',' ')}</dt><dd>{String(v)}</dd></div>)}</dl>
 <form onSubmit={async e=>{e.preventDefault();const f=new FormData(e.currentTarget);try{await api('/properties/admin/prices','PUT',{scope:f.get('scope'),category:f.get('category'),amount:Number(f.get('xp')),enabled:f.get('enabled')==='on'});setMsg('Price rule saved.')}catch(e){setMsg((e as Error).message)}}}>
 <h3>XP pricing</h3><label>City, country code, property ID or global (*)<input name="scope" required list="property-city-scopes"/></label><datalist id="property-city-scopes">{cities.map(c=><option key={c.city} value={c.city}/>)}</datalist>
 <label>Category<select name="category">{['house','apartments','townhouse','villa','residential','office','shop','commercial','building'].map(c=><option key={c}>{c}</option>)}</select></label>
 <label>XP price<input name="xp" type="number" min="1" max="1000000000" required/></label><label><input type="checkbox" name="enabled" defaultChecked/>Purchases enabled</label><button>Save pricing</button></form>
 <h3>City inventory</h3><table><thead><tr><th>City</th><th>Eligible</th><th>Registered</th><th>Inventory</th></tr></thead><tbody>{cities.map(c=><tr key={c.city}><td>{c.city}</td><td>{c.eligible}</td><td>{c.registered}</td><td><button onClick={async()=>{try{await api('/properties/admin/register/'+c.city,'POST',{});setRev(v=>v+1)}catch(e){setMsg((e as Error).message)}}}>Register</button></td></tr>)}</tbody></table></section>;
}
