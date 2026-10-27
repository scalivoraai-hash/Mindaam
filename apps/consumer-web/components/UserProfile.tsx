'use client';
import {useEffect,useRef,useState} from 'react';
import {Instagram,Facebook,Linkedin,Youtube,Link as LinkIcon,UserPlus,UserCheck,MessageCircle,Phone,Video,ExternalLink,X} from 'lucide-react';
import {api,Data} from '@/lib/api';
import AvatarPreview from './AvatarPreview';
import {PrivatePhoto} from './ProfilePhotos';
import {ProfileLocation} from './ProfileEditor';

export function openUserProfile(id:string){window.dispatchEvent(new CustomEvent('mindaam-profile',{detail:id}))}
export function ProfileButton({id,children='View profile'}:{id:string;children?:React.ReactNode}){return <button type="button" onClick={()=>openUserProfile(id)}>{children}</button>}
const icons:Record<string,any>={instagram:Instagram,facebook:Facebook,linkedin:Linkedin,youtube:Youtube};
export function UserProfile({id,username,compact=false}:{id?:string;username?:string;compact?:boolean}){
 const [p,setP]=useState<Data|null>(null),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[tab,setTab]=useState('About');
 const path=username?'/profiles/by-name/'+encodeURIComponent(username):'/profiles/'+encodeURIComponent(id||'');
 useEffect(()=>{let alive=true;setP(null);setError('');setNotice('');setTab('About');api(path).then(d=>{if(alive)setP(d)}).catch(e=>{if(alive)setError(e.message)});return()=>{alive=false}},[path]);
 const action=async(kind:string)=>{if(!p||busy)return;setBusy(true);setError('');try{await api(`/social/${p.id}/${kind}`,'POST',{});if(kind==='block'){setP(null);setNotice('Player blocked.')}else setP(await api(path))}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const invite=async(kind:string)=>{if(!p||busy)return;setBusy(true);try{await api('/talk/request','POST',{target_id:p.id,kind});window.dispatchEvent(new Event('pulse-talk-refresh'));window.dispatchEvent(new Event('pulse-media-refresh'));setNotice('Request sent. Devices stay off until you choose Join.')}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const share=async()=>{if(!p)return;try{await navigator.clipboard.writeText(location.origin+'/u/'+encodeURIComponent(p.username));setNotice('Profile link copied.')}catch{setError('Could not copy the link. Open the profile link below to copy its address.')}};
 const r=p?.relationship||{};
 return <article className={'user-profile '+(compact?'compact':'')} data-theme={p?.theme||'Midnight Neon'} aria-busy={busy}>
 {p?<><div className="profile-banner">{p.photos?.cover&&<PrivatePhoto path={p.photos.cover} alt="Profile cover"/>}</div><header className="profile-identity"><span className="profile-monogram" aria-hidden="true">{p.photos?.picture?<PrivatePhoto path={p.photos.picture} alt={p.display_name||p.username}/>:<>{(p.display_name||p.username).slice(0,2)}</>}</span><div><h2>{p.display_name||p.username}</h2><p>@{p.username}{p.online?' · Online':''}</p></div></header>
 <p className="profile-bio">{p.bio||'No bio shared yet.'}</p><ProfileLocation profile={p}/>
 <nav className="profile-links" aria-label="Social links">{Object.entries(p.links||{}).map(([platform,url])=>{const Icon=icons[platform]||LinkIcon;return <a key={platform} href={String(url)} target="_blank" rel="noopener noreferrer nofollow ugc" title={platform}><Icon size={18}/><span>{platform}</span></a>})}</nav>
 <div className="profile-counts">{Object.entries(p.counts||{}).map(([label,count])=><span key={label}><b>{String(count)}</b> {label}</span>)}</div>
 {!p.own&&<div className="profile-actions"><button disabled={busy} onClick={()=>action(r.following?'unfollow':'follow')}>{r.following?'Unfollow':'Follow'}</button><button disabled={busy} onClick={()=>action(r.friend?'remove':r.incoming?'accept':r.requested?'cancel':'friend')}>{r.friend?<UserCheck size={16}/>:<UserPlus size={16}/>} {r.friend?'Remove friend':r.incoming?'Accept friend':r.requested?'Cancel request':'Add friend'}</button>{r.incoming&&<button disabled={busy} onClick={()=>action('decline')}>Decline</button>}{[['text','Message',MessageCircle],['voice','Voice',Phone],['liveface','LiveFace',Video]].map(([kind,label,Icon]:any)=><button key={kind} title={label} aria-label={label} disabled={busy} onClick={()=>invite(kind)}><Icon size={17}/></button>)}</div>}
 <div className="profile-actions">{compact&&<button onClick={()=>openUserProfile(p.id)}>View full profile</button>}<a href={'/u/'+encodeURIComponent(p.username)} target="_blank" rel="noopener noreferrer"><ExternalLink size={15}/> Profile link</a><button onClick={share}>Copy link</button></div>
 {!compact&&<><nav className="profile-tabs" aria-label="Profile sections">{['About','Events','Activity','Avatar'].map(t=><button key={t} aria-pressed={tab===t} onClick={()=>setTab(t)}>{t}</button>)}</nav>{tab==='About'&&<section><p>{p.category||'Personal profile'} · Joined {new Date(p.joined_at*1000).toLocaleDateString()}</p><p>{(p.public_interests||[]).join(' · ')||'No interests shared.'}</p><p>{(p.languages||[]).join(' · ')}</p></section>}{tab==='Events'&&<section>{p.events?.length?p.events.map((e:Data)=><a className="profile-event" key={e.id} href={'/?event='+encodeURIComponent(e.id)} onClick={()=>window.dispatchEvent(new CustomEvent('pulse-open-event',{detail:e.id}))}><b>{e.title}</b><span>{new Date(e.starts_at*1000).toLocaleString()} · {e.state}</span></a>):<p>No public events to show.</p>}</section>}{tab==='Avatar'&&<AvatarPreview appearance={p.avatar||{}}/>}{tab==='Activity'&&<p>{p.counts.events} public events hosted. Private activity is not displayed.</p>}</>}
 {!p.own&&<details><summary>Safety options</summary><div className="profile-actions"><button disabled={busy} onClick={()=>action('block')}>Block</button><button disabled={busy} onClick={async()=>{const details=prompt('Describe the profile issue for moderation.');if(!details)return;setBusy(true);try{await api('/reports','POST',{target_id:p.id,category:'safety',details});setNotice('Report submitted.')}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>Report profile</button></div></details>}
 </>:!error&&!notice&&<p role="status">Loading profile…</p>}{error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
 </article>
}
export default function ProfileOverlay(){
 const [id,setId]=useState<string|null>(null);const dialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const show=(e:Event)=>{const id=(e as CustomEvent).detail;if(typeof id==='string'&&id.length<=64)setId(id)};window.addEventListener('mindaam-profile',show);return()=>window.removeEventListener('mindaam-profile',show)},[]);
 useEffect(()=>{if(id&&!dialog.current?.open)dialog.current?.showModal()},[id]);
 return <dialog ref={dialog} className="profile-dialog" aria-label="Player profile" onClose={()=>setId(null)} onClick={e=>{if(e.target===dialog.current)dialog.current?.close()}}><button className="profile-close" aria-label="Close profile" onClick={()=>dialog.current?.close()}><X size={21}/></button>{id&&<UserProfile key={id} id={id}/>}</dialog>
}
