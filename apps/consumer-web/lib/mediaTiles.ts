import {Participant,Track} from 'livekit-client';
export type Presentation={presenter_id?:string|null;screen_track_id?:string|null;screen_audio_track_id?:string|null};
/** SID-owned playback; camera, microphone and presentation sources never share a slot. */
export class MediaTiles {
 private tracks=new Map<string,{track:Track;element:HTMLMediaElement}>();
 private tiles=new Map<string,HTMLElement>();
 private stageVideo:HTMLVideoElement|null=null;
 private screens:HTMLElement;
 constructor(private host:HTMLElement,private muted:(id:string)=>boolean,private blocked:()=>void){
  this.screens=document.createElement('div');this.screens.className='presentation-sources';this.screens.setAttribute('aria-hidden','true');host.append(this.screens);
 }
 sync(participants:Participant[],kind:string,speakers:string[]=[],presentation:Presentation={}){
  const wanted=new Set<string>(),people=new Set(participants.map(p=>p.identity));
  let sharedVideo:HTMLVideoElement|null=null;
  participants.forEach((participant,index)=>{
   let tile=this.tiles.get(participant.identity);
   if(!tile){tile=document.createElement('div');tile.className='media-tile '+(participant.isLocal?'local-tile':'remote-tile');tile.dataset.peerId=participant.identity;this.tiles.set(participant.identity,tile);this.host.append(tile)}
   tile.classList.toggle('event-speaker',speakers.includes(participant.identity));tile.classList.toggle('is-speaking',participant.isSpeaking);tile.style.setProperty('--media-index',String(index));
   let name=tile.querySelector('span');if(!name){name=document.createElement('span');tile.append(name)}name.textContent=participant.name||'Explorer';
   let hasVideo=false;
   participant.trackPublications.forEach(publication=>{
    const track=publication.track;if(!track||(participant.isLocal&&track.kind===Track.Kind.Audio))return;
    const source=publication.source;
    const screen=source===Track.Source.ScreenShare,screenAudio=source===Track.Source.ScreenShareAudio;
    const video=track.kind===Track.Kind.Video;
    // Accept a screen only when the authenticated Event state selects its owner
    // and provider-confirmed SID. A stale publisher cannot take over the wall.
    if(screen||screenAudio){
     if(participant.identity!==presentation.presenter_id||publication.trackSid!==(screen?presentation.screen_track_id:presentation.screen_audio_track_id))return;
    }else if(source!==Track.Source.Camera&&source!==Track.Source.Microphone)return;
    const key=participant.identity+':'+publication.trackSid;wanted.add(key);
    let existing=this.tracks.get(key);
    if(existing&&existing.track!==track){existing.track.detach(existing.element);existing.element.remove();this.tracks.delete(key);existing=undefined}
    if(!existing){
     const element=track.attach();element.autoplay=true;element.setAttribute('playsinline','');element.dataset.trackSource=source;element.dataset.peerId=participant.identity;
     existing={track,element};this.tracks.set(key,existing);(screen||screenAudio?this.screens:tile!).append(element);
     if(!video){try{const sound=JSON.parse(localStorage.getItem('pulse-sound')||'{}');element.volume=(sound.master??.55)*(sound.voice??.8)}catch{}}
     void element.play().catch(e=>{if(e.name==='NotAllowedError')this.blocked()});
    }
    // Video elements are always muted: audio has its own source-owned element.
    existing.element.muted=video||participant.isLocal||publication.isMuted||this.muted(participant.identity);
    existing.element.hidden=video&&publication.isMuted;
    if(video&&!publication.isMuted){if(screen)sharedVideo=existing.element as HTMLVideoElement;else hasVideo=true}
   });
   tile.classList.toggle('has-video',hasVideo);tile.querySelectorAll('.media-avatar,.media-tile-status').forEach(el=>el.remove());
   if(!hasVideo){const avatar=document.createElement('b');avatar.className='media-avatar';avatar.textContent=(participant.name||'Explorer').slice(0,2).toUpperCase();tile.append(avatar);const state=document.createElement('small');state.className='media-tile-status';state.textContent=kind==='voice'?'🎙 Voice connected':'🎥 Camera off';tile.append(state)}
  });
  for(const [id,owned] of this.tracks)if(!wanted.has(id)){owned.track.detach(owned.element);owned.element.remove();this.tracks.delete(id)}
  for(const [id,tile] of this.tiles)if(!people.has(id)){tile.remove();this.tiles.delete(id)}
  const video=sharedVideo||speakers.map(id=>this.tiles.get(id)?.querySelector<HTMLVideoElement>('video[data-track-source="camera"]:not([hidden])')).find(Boolean)||null;
  if(video!==this.stageVideo){
   if(this.stageVideo)delete this.stageVideo.dataset.stageSelected;
   this.stageVideo=video;if(video)video.dataset.stageSelected='true';
   window.dispatchEvent(new CustomEvent('pulse-stage-media',{detail:{video,source:sharedVideo?'screen_share':video?'camera':'default'}}));
  }
 }
 refreshMute(){for(const {element,track} of this.tracks.values())if(track.kind===Track.Kind.Audio)element.muted=this.muted(element.dataset.peerId||'')}
 dispose(){window.dispatchEvent(new CustomEvent('pulse-stage-media',{detail:{video:null,source:'default'}}));this.stageVideo=null;for(const {track,element} of this.tracks.values()){track.detach(element);element.remove()}this.tracks.clear();this.tiles.forEach(t=>t.remove());this.tiles.clear();this.screens.remove()}
}
