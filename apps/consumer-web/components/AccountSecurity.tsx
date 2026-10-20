'use client';
import {useEffect,useState} from 'react';
import {api,Data} from '@/lib/api';
export default function AccountSecurity({onLogout}:{onLogout:()=>void}){
 const [sessions,setSessions]=useState<Data[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{api('/auth/sessions').then(setSessions).catch(e=>setError(e.message))},[]);
 return <section><h3>Account security</h3><p>{sessions.length} active session{sessions.length===1?'':'s'}</p>{sessions.map((s,i)=><p className="tiny" key={i}>Signed in {new Date(s.created_at*1000).toLocaleString()} · Expires {new Date(s.expires_at*1000).toLocaleString()}</p>)}<details><summary>Change password</summary><form onSubmit={async e=>{e.preventDefault();const f=new FormData(e.currentTarget);setBusy(true);setError('');try{await api('/auth/change-password','POST',Object.fromEntries(f));onLogout()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}><label>Current password<input name="current_password" type="password" required autoComplete="current-password"/></label><label>New password<input name="password" type="password" minLength={12} maxLength={128} required autoComplete="new-password"/></label><label>Confirm new password<input name="confirm_password" type="password" required autoComplete="new-password"/></label><p>Changing your password signs out every device.</p><button disabled={busy}>Change password</button></form></details>{error&&<p role="alert">{error}</p>}</section>
}
