export type Data=Record<string,any>;
export async function api(path:string,method='GET',data?:unknown):Promise<any>{
 const token=typeof window!=='undefined'?sessionStorage.getItem('pulse-token'):null;
 const attempts=method==='GET'?3:1;
 for(let attempt=0;attempt<attempts;attempt++){
  try{
   if(typeof navigator!=='undefined'&&!navigator.onLine)throw new Error('Offline. Check your internet connection.');
   const signal=AbortSignal.timeout(12000);
   const res=await fetch(`/api${path}`,{method,signal,headers:{'Content-Type':'application/json','X-Pulse-Client':'web',...(token?{Authorization:`Bearer ${token}`}:{})},...(data!==undefined?{body:JSON.stringify(data)}:{})});
   let value:any;try{value=await res.json()}catch(e){
    // A timeout can occur after headers arrive. Never return a fabricated success
    // body to callers that expect a user, collection or social-activity snapshot.
    if(signal.aborted)throw signal.reason;
    if(e instanceof TypeError)throw e;
    if(res.ok)throw new Error('Unable to read the server response. Please retry.');
    value={detail:`Server error (${res.status}). Please retry.`};
   }
   if(res.status>=500&&attempt<attempts-1){await new Promise(r=>setTimeout(r,700*2**attempt));continue}
   if(!res.ok&&['WORLD_LOCKED','STARTER_CONFIRMATION_REQUIRED'].includes(value.detail?.code)&&typeof window!=='undefined')window.dispatchEvent(new CustomEvent('mylil-world-locked',{detail:value.detail.destination_id}));
   if(!res.ok)throw new Error(typeof value.detail==='string'?value.detail:typeof value.detail?.message==='string'?value.detail.message:res.status===422?'Please check the details and try again.':'Unable to complete this action. Please try again.');return value;
  }catch(e){if(attempt<attempts-1&&((e as Error).name==='TimeoutError'||e instanceof TypeError)){await new Promise(r=>setTimeout(r,700*2**attempt));continue}throw new Error((e as Error).name==='TimeoutError'?'Connection timed out. Retry to check the result.':e instanceof TypeError?'Connection interrupted. Please try again.':(e as Error).message)}
 }
}
export const list=(data:any,key?:string):Data[]=>Array.isArray(data)?data:Array.isArray(data?.[key||'items'])?data[key||'items']:[];
