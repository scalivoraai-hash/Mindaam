'use client';
import {ScreenShare,Square,Settings2} from 'lucide-react';
import {useEffect,useRef,useState} from 'react';
import {LocalTrack,Room,RoomEvent,Track} from 'livekit-client';
import {api,Data} from '@/lib/api';
/** Explicit capture gesture; the browser picker runs before network waits. */
export default function EventScreenShare({room,event,onChange}:{room:Room;event:Data;onChange:()=>Promise<void>}){
 const [busy,setBusy]=useState(false),[sharing,setSharing]=useState(false),[audio,setAudio]=useState(false),[notice,setNotice]=useState('');
 const capture=useRef<LocalTrack[]>([]),request=useRef(''),lock=useRef(false),alive=useRef(true),generation=useRef(0),sid=useRef(''),publishedRevision=useRef(0);
 const live=useRef(event);live.current=event;
 const supported=typeof navigator!=='undefined'&&typeof navigator.mediaDevices?.getDisplayMedia==='function'&&window.isSecureContext;
 async function stop(){
  generation.current++;const owned=capture.current,requestId=request.current;request.current='';capture.current=[];sid.current='';publishedRevision.current=0;
  for(const track of owned){track.mediaStreamTrack.onended=null;track.stop();void room.localParticipant.unpublishTrack(track).catch(()=>{})}
  if(alive.current){setSharing(false);setNotice('')}
  if(requestId)try{await api(`/events/${event.event_id}/presentation/stop`,'POST',{request_id:requestId});await onChange()}catch{if(alive.current)setNotice('Presentation stopped on this device. Reconnecting to the event…')}
 }
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;void stop()}},[room,event.event_id]);
 useEffect(()=>{
  const permissions=()=>{
   const p=room.localParticipant.permissions;
   if(capture.current.length&&p&&(!p.canPublish||!p.canPublishSources.includes(Track.sourceToProto(Track.Source.ScreenShare))))void stop();
  };
  room.on(RoomEvent.ParticipantPermissionsChanged,permissions);return()=>{room.off(RoomEvent.ParticipantPermissionsChanged,permissions)};
 },[room]);
 // The authenticated Event snapshot also revokes capture. Provider permission
 // notifications can arrive after track removal; neither path waits for a heartbeat.
 useEffect(()=>{
  const p=event.presentation;
  if(sharing&&sid.current&&p&&p.revision>=publishedRevision.current&&(p.presenter_id!==room.localParticipant.identity||p.screen_track_id!==sid.current))void stop();
 },[sharing,event.presentation?.revision,event.presentation?.presenter_id,event.presentation?.screen_track_id,room]);
 useEffect(()=>{
  if(!sharing)return;
  const beat=async()=>{if(!sid.current)return;try{await api(`/events/${event.event_id}/presentation/heartbeat`,'POST',{screen_track_id:sid.current})}catch{const p=live.current.presentation;if(p?.presenter_id!==room.localParticipant.identity){await stop();setNotice('The host has ended or switched this presentation.')}}};
  const timer=setInterval(beat,10000);return()=>clearInterval(timer);
 },[sharing,event.event_id,room]);
 async function start(){
  if(lock.current||!supported||!live.current.presentation?.may_start)return;
  lock.current=true;setBusy(true);setNotice('');const attempt=++generation.current;request.current=crypto.randomUUID();let tracks:LocalTrack[]=[];
  try{
   // The user chooses a tab/window/screen. Nothing is captured on join or approval.
   tracks=await room.localParticipant.createScreenTracks({audio,resolution:{width:1280,height:720,frameRate:15},contentHint:'detail',selfBrowserSurface:'exclude'});
   if(!alive.current||attempt!==generation.current){tracks.forEach(t=>t.stop());return}
   await api(`/events/${event.event_id}/presentation/start`,'POST',{request_id:request.current});
   if(!alive.current||attempt!==generation.current){tracks.forEach(t=>t.stop());return}
   await new Promise<void>((resolve,reject)=>{let timeout:ReturnType<typeof setTimeout>;const check=()=>{const p=room.localParticipant.permissions;if(p?.canPublish&&p.canPublishSources.includes(Track.sourceToProto(Track.Source.ScreenShare))){room.off(RoomEvent.ParticipantPermissionsChanged,check);clearTimeout(timeout);resolve()}};timeout=setTimeout(()=>{room.off(RoomEvent.ParticipantPermissionsChanged,check);reject(new Error('permission'))},4000);room.on(RoomEvent.ParticipantPermissionsChanged,check);check()});
   if(!alive.current||attempt!==generation.current){tracks.forEach(t=>t.stop());return}
   capture.current=tracks;
   let videoId='';
   for(const track of tracks){const publication=await room.localParticipant.publishTrack(track,{source:track.source,videoEncoding:{maxBitrate:1800000,maxFramerate:15},simulcast:false});if(track.source===Track.Source.ScreenShare){videoId=publication.trackSid;track.mediaStreamTrack.onended=()=>{void stop()}}}
   if(!videoId)throw new Error('capture');
   const confirmed=await api(`/events/${event.event_id}/presentation/published`,'POST',{request_id:request.current,screen_track_id:videoId});
   if(!alive.current||attempt!==generation.current){await stop();return}
   sid.current=videoId;publishedRevision.current=confirmed.revision;setSharing(true);await onChange().catch(()=>{});
   if(!alive.current||attempt!==generation.current)return;
   setNotice(audio&&!tracks.some(t=>t.source===Track.Source.ScreenShareAudio)?'Screen is live. This browser or selected source did not provide audio.':'');
  }catch(e){tracks.forEach(t=>t.stop());await stop();if(alive.current)setNotice((e as Error).name==='NotAllowedError'?'Screen sharing cancelled. Your microphone and camera are unchanged.':'Unable to share this screen. Check host approval and try again.')}
  finally{lock.current=false;if(alive.current)setBusy(false)}
 }
 const permission=event.presentation||{};
 return <div className="event-share-controls" data-event-media={event.event_id} aria-label="Screen sharing controls">
  {!supported?<button disabled aria-label="Screen sharing unavailable on this device" title="You can still view presentations"><ScreenShare size={19}/></button>:sharing?<button aria-label="Stop sharing" title="Stop sharing" disabled={busy} onClick={()=>void stop()}><Square size={19}/></button>:permission.may_start?<><details className="share-audio-options"><summary title="Screen audio options" aria-label="Screen audio options"><Settings2 size={18}/></summary><label className="check"><input type="checkbox" checked={audio} onChange={e=>setAudio(e.target.checked)}/>Include audio if supported</label></details><button className="primary" aria-label={busy?'Preparing screen…':'Share screen'} title="Share screen" disabled={busy} onClick={()=>void start()}><ScreenShare size={19}/></button></>:permission.my_share_state==='allowed'?<button disabled aria-label="Sharing approved. Waiting for host" title="Sharing approved. Waiting for host"><ScreenShare size={19}/></button>:<button aria-label={permission.my_share_state==='pending'?'Share request pending':'Request to share screen'} title={permission.my_share_state==='pending'?'Share request pending':'Request to share screen'} disabled={busy||permission.my_share_state==='pending'} onClick={async()=>{if(lock.current)return;lock.current=true;setBusy(true);try{await api(`/events/${event.event_id}/presentation/request`,'POST',{});await onChange()}catch{setNotice('Unable to send the request. Please try again.')}finally{lock.current=false;setBusy(false)}}}><ScreenShare size={19}/></button>}
  {notice&&<small role="status">{notice}</small>}
 </div>
}
