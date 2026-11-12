import {api,type Data} from './api.ts';
// Only public bundled geography; never cache world, presence, entitlement or user data.
const pending=new Map<string,Promise<Data>>();
export function loadGeography(city:string):Promise<Data>{
 const found=pending.get(city);if(found)return found;
 // The profile travels with the map, so a separate short request cannot
 // silently downgrade and cache a different world during a busy frame.
 const request=api('/geography/'+encodeURIComponent(city)).then(async geography=>{
  if(['standard','cinematic-world-v1','cinematic-world-v2'].includes(geography.visual_profile))return geography;
  // An older backend may serve a request during a gradual rollout. Retain
  // compatibility through the normal API request policy, never a silent
  // short-timeout downgrade cached for the rest of the session.
  const profile=await api('/visual-profile/'+encodeURIComponent(city));
  if(profile.city!==city||!['standard','cinematic-world-v1','cinematic-world-v2'].includes(profile.profile))throw new Error('World presentation is unavailable. Please retry.');
  return {...geography,visual_profile:profile.profile};
 }).catch(error=>{pending.delete(city);throw error});
 pending.set(city,request);if(pending.size>4)pending.delete(pending.keys().next().value!);
 return request;
}
