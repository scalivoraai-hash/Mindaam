'use client';
import {useState} from 'react';
import Link from 'next/link';
import BrandMark from '@/components/BrandMark';
import ThemeToggle from '@/components/ThemeToggle';
import {api} from '@/lib/api';

export default function AdminLogin(){
 const [visible,setVisible]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[recovery,setRecovery]=useState(false),[message,setMessage]=useState('');
 return <main className="identity-page"><Link className="brand" href="/"><BrandMark wordmark/></Link><ThemeToggle/><section className="auth-card glass"><p className="eyebrow">OWNER &amp; PLATFORM OPERATIONS</p><h1>{recovery?'Recover admin access':'Admin sign in'}</h1><p>{recovery?'A single-use reset link will be sent if the account is eligible.':'Sign in with your authorised Mindaam account.'}</p><form onSubmit={async e=>{e.preventDefault();setError('');setMessage('');setBusy(true);const f=new FormData(e.currentTarget);try{if(recovery){const d=await api('/auth/forgot-password','POST',{email:f.get('email')});setMessage(d.message||'If eligible, check your account email for a reset link.')}else{const d=await api('/auth/admin-login','POST',{identifier:f.get('identifier'),password:f.get('password')});if(d.user?.role!=='super_admin')throw new Error('Unable to sign in.');sessionStorage.removeItem('pulse-token');location.assign('/eluvathingal')}}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>
 {recovery?<label>Email address<input name="email" type="email" autoComplete="email" required maxLength={254}/></label>:<><label>Email or username<input name="identifier" autoComplete="username" required maxLength={254}/></label><label>Password<input name="password" type={visible?'text':'password'} autoComplete="current-password" required maxLength={128}/></label><button type="button" aria-pressed={visible} onClick={()=>setVisible(!visible)}>{visible?'Hide password':'Show password'}</button></>}
 <button className="primary wide" disabled={busy}>{busy?'Please wait…':recovery?'Send reset link':'Sign In'}</button></form>{error&&<p role="alert" className="notice">{error}</p>}{message&&<p role="status">{message}</p>}<button className="text-button" onClick={()=>{setRecovery(!recovery);setError('');setMessage('')}}>{recovery?'Back to admin sign in':'Forgot password?'}</button><Link href="/">Back to Mindaam</Link></section></main>
}
