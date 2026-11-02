import {api,Data} from './api';
// Only public bundled geography; never cache world, presence, entitlement or user data.
const pending=new Map<string,Promise<Data>>();
export function loadGeography(city:string):Promise<Data>{
 const found=pending.get(city);if(found)return found;
 const profile=city==='milton-keynes'?fetch('/api/visual-profile/'+city,{cache:'no-store',signal:AbortSignal.timeout(1500)}).then(r=>r.ok?r.json():null).then(v=>v?.city===city&&v?.profile==='cinematic-world-v1'?'cinematic-world-v1':'standard').catch(()=>'standard'):Promise.resolve('standard');
 const request=Promise.all([api('/geography/'+encodeURIComponent(city)),profile]).then(([geography,visual_profile])=>({...geography,visual_profile})).catch(error=>{pending.delete(city);throw error});
 pending.set(city,request);if(pending.size>4)pending.delete(pending.keys().next().value!);
 return request;
}
