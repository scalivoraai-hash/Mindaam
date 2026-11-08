'use client';
import {useState} from 'react';
import {api,Data} from '@/lib/api';

export function ProfileCorrection({user,profile,onSaved}:{user:Data;profile:Data;onSaved:()=>Promise<void>}){
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 async function save(event:React.FormEvent<HTMLFormElement>){
  event.preventDefault();const fields=new FormData(event.currentTarget);
  if(!confirm(`Save this documented profile correction for ${user.username}?`))return;
  setBusy(true);setError('');setNotice('');
  try{
   await api(`/super-admin/users/${user.id}/profile`,'PATCH',{
    expected:profile,reason:fields.get('reason'),profile:{display_name:fields.get('display_name'),bio:fields.get('bio'),
     languages:String(fields.get('languages')||'').split(',').map(s=>s.trim()).filter(Boolean),theme:fields.get('theme')}});
   await onSaved();setNotice('Profile correction saved and recorded in the audit log.');
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 if(['admin','super_admin'].includes(user.role))return <p>Privileged profiles require separate operational review.</p>;
 return <form className="ops-record" onSubmit={save}><h3>Correct profile</h3>
  <p>Changes update this user’s saved profile. Record the reason for the correction.</p>
  <div className="ops-fields" key={JSON.stringify(profile)}>
   <label>Display name<input name="display_name" maxLength={80} defaultValue={profile.display_name||''}/></label>
   <label>Languages, separated by commas<input name="languages" defaultValue={(profile.languages||[]).join(', ')}/></label>
   <label>Biography<textarea name="bio" maxLength={300} defaultValue={profile.bio||''}/></label>
   <label>Profile theme<select name="theme" defaultValue={profile.theme||'Midnight Neon'}>{['Midnight Neon','Aurora','Ocean','Sunset','Electric Violet','Minimal Light'].map(t=><option key={t}>{t}</option>)}</select></label>
  </div><label>Documented reason<textarea name="reason" required minLength={12} maxLength={500}/></label>
  {error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
  <button className="primary" disabled={busy}>{busy?'Saving…':'Review and save profile'}</button>
 </form>
}

export function PaymentReconciliation({user,payment,onSaved}:{user:Data;payment:Data;onSaved:()=>Promise<void>}){
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 if(payment.business_id||!payment.provider_id||payment.refunded_pence||payment.dispute_status)return null;
 async function reconcile(){
  const reason=prompt('Document why this existing purchase needs reconciliation (at least 12 characters)');
  if(!reason||reason.trim().length<12)return;
  if(!confirm(`Verify purchase ${payment.id} with Stripe and recover up to ${payment.credits} PC for ${user.username}? An already recorded purchase cannot be credited twice.`))return;
  setBusy(true);setError('');setNotice('');
  try{
   const result=await api(`/super-admin/users/${user.id}/payments/${payment.id}/reconcile`,'POST',{reason,confirmed:true});
   setNotice(result.already_recorded?'This purchase is already recorded. No duplicate credits were issued.':`Purchase verified. Recorded transaction ${result.transaction.id}: ${result.transaction.previous_balance} → ${result.transaction.balance} PC.`);
   await onSaved();
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 return <div><p>Recover only credits backed by this existing, verified purchase.</p>
  <button disabled={busy} onClick={reconcile}>{busy?'Verifying purchase…':'Verify and reconcile purchase'}</button>
  {error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
 </div>
}
