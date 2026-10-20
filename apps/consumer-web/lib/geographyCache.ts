import {api,Data} from './api';
// Only public bundled geography; never cache world, presence, entitlement or user data.
const pending=new Map<string,Promise<Data>>();
export function loadGeography(city:string):Promise<Data>{
 const found=pending.get(city);if(found)return found;
 const request=api('/geography/'+encodeURIComponent(city)).catch(error=>{pending.delete(city);throw error});
 pending.set(city,request);if(pending.size>4)pending.delete(pending.keys().next().value!);
 return request;
}
