'use client';
import {Expand,Maximize,ArrowLeft} from 'lucide-react';
import {useEffect,useRef,useState} from 'react';
import {Data} from '@/lib/api';
/** Playback-only local layout. No API calls, room ownership, capture or shared state. */
export default function PresentationView({event}:{event:Data}){
 const [mode,setMode]=useState<'mini'|'normal'|'expanded'|'fullscreen'>('mini'),[source,setSource]=useState('default');
 const video=useRef<HTMLVideoElement>(null),selected=useRef<HTMLVideoElement|null>(null);
 useEffect(()=>{
  const render=(e:Event)=>{const data=(e as CustomEvent).detail||{};selected.current=data.video||null;setSource(data.source||'default');
   if(video.current){video.current.srcObject=data.video?.srcObject||null;if(data.video)void video.current.play().catch(()=>{})}

  };
  const open=()=>{setMode('normal')};
  const escape=(e:KeyboardEvent)=>{if(e.key==='Escape')setMode(current=>current==='fullscreen'||current==='expanded'?'normal':current)};
  window.addEventListener('pulse-stage-media',render);window.addEventListener('pulse-stage-view',open);window.addEventListener('keydown',escape);
  const initial=document.querySelector<HTMLVideoElement>('video[data-stage-selected="true"]');render(new CustomEvent('initial',{detail:{video:initial,source:initial?.dataset.trackSource||'default'}}));
  return()=>{window.removeEventListener('pulse-stage-media',render);window.removeEventListener('pulse-stage-view',open);window.removeEventListener('keydown',escape);if(video.current)video.current.srcObject=null};
 },[]);
 const view=(next:typeof mode)=>{setMode(next)};
 return <section className={'presentation-view presentation-'+mode} hidden={mode==='mini'} aria-label="Event presentation" data-view-mode={mode} role={mode==='fullscreen'?'dialog':undefined} aria-modal={mode==='fullscreen'||undefined}>
  <header><span><b>{source==='screen_share'?'LIVE PRESENTATION':'MINDAAM LIVE'}</b><small>{event.event_title||event.title}</small></span>{mode==='mini'?<button onClick={()=>view('normal')}>View stage ↗</button>:<button aria-label="Minimise presentation" onClick={()=>view('mini')}>−</button>}</header>
  <div className="presentation-picture" hidden={mode==='mini'}><video ref={video} autoPlay playsInline muted hidden={source==='default'}/>{source==='default'&&<div className="event-wall-poster"><span>MINDAAM LIVE</span><h2>{event.event_title||event.title}</h2><p>{event.event_description||event.description||'A place to connect, discover and share.'}</p><small>● Event live · Your stage is ready</small></div>}</div>
  {mode!=='mini'&&<footer><button aria-label={mode==='expanded'?'Normal view':'Expand'} title={mode==='expanded'?'Normal view':'Expand'} onClick={()=>view(mode==='expanded'?'normal':'expanded')}><Expand size={19}/></button><button aria-label={mode==='fullscreen'?'Exit full screen':'Full screen'} title={mode==='fullscreen'?'Exit full screen':'Full screen'} onClick={()=>view(mode==='fullscreen'?'normal':'fullscreen')}><Maximize size={19}/></button><button aria-label="Back to Event" title="Back to Event" onClick={()=>view('mini')}><ArrowLeft size={19}/></button><small>Your view only</small></footer>}
 </section>
}
