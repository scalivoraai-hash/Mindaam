// Local microphones must never get a playback element, even a detached one.
export function attachable(local:boolean,kind:string,muted:boolean,key:string,seen:Set<string>){if(muted||(local&&kind==='audio')||seen.has(key))return false;seen.add(key);return true}
export function speechConstraints(supported:{echoCancellation?:boolean;noiseSuppression?:boolean;autoGainControl?:boolean}){return {...(supported.echoCancellation?{echoCancellation:true}:{}),...(supported.noiseSuppression?{noiseSuppression:true}:{}),...(supported.autoGainControl?{autoGainControl:true}:{})}}
