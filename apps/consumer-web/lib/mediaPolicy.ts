import defaults from '../../../shared/media-policy.json' with {type:'json'};
export type MediaPolicy=typeof defaults;
export const MEDIA_POLICY:MediaPolicy=defaults;
export type SubscriptionTrack={sid:string;peer:string;source:string;muted:boolean};
export type SubscriptionContext={event:boolean;speakers:string[];presenter?:string;screen?:string;screenAudio?:string;display:'mini'|'expanded'|'fullscreen';hidden:boolean;visiblePeers?:Set<string>;primary?:string;policy:MediaPolicy};
/** Pure interest selection, independent of playback elements and join order. */
export function selectTracks(tracks:SubscriptionTrack[],context:SubscriptionContext){
 const selected=new Set<string>(), {policy}=context;
 const stage=(t:SubscriptionTrack)=>!context.event||context.speakers.includes(t.peer);
 for(const t of tracks)if(t.source==='microphone'&&stage(t)||t.source==='screen_share_audio'&&t.peer===context.presenter&&t.sid===context.screenAudio)selected.add(t.sid);
 if(context.hidden)return selected;
 const screen=tracks.find(t=>t.source==='screen_share'&&t.peer===context.presenter&&t.sid===context.screen);
 if(screen)selected.add(screen.sid);
 const cameras=tracks.filter(t=>t.source==='camera'&&!t.muted&&stage(t)&&(context.event||context.display!=='mini'||!context.visiblePeers||context.visiblePeers.has(t.peer)));
 cameras.sort((a,b)=>Number(b.peer===context.primary)-Number(a.peer===context.primary)||a.peer.localeCompare(b.peer));
 for(const t of cameras.slice(0,Math.max(0,policy.max_visible_video_subscriptions-(screen?1:0))))selected.add(t.sid);
 return selected;
}
export function videoHeight(display:SubscriptionContext['display'],policy:MediaPolicy,screen=false){return screen||display!=='mini'?policy.fullscreen_video_max:policy.avatar_video_max}
