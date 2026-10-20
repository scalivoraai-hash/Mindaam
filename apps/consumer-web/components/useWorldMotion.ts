'use client';
import {useCallback,useRef,useState} from 'react';
import {Data} from '@/lib/api';
import {acceptMotion,MotionStall,MotionTransition} from '@/lib/motionState';
import {HeldMovement} from '@/lib/movement';

export function useWorldMotion(world:Data|null,setWorld:React.Dispatch<React.SetStateAction<Data|null>>,mode:string,enabled:boolean,onError:(s:string)=>void){
 const latest=useRef({world,mode,enabled,onError});latest.current={world,mode,enabled,onError};
 const held=useRef(new HeldMovement()),location=useRef('');
 const socket=useRef<WebSocket|null>(null),sequence=useRef(0),pending=useRef<Data|null>(null),inFlight=useRef(false);
 const stall=useRef(new MotionStall()),[stalled,setStalled]=useState(false);
 const transitionGate=useRef(new MotionTransition()),[transitioning,setTransitioning]=useState(false);
 const receive=useCallback((d:Data)=>{
  if(!transitionGate.current.accepts(d.seq))return;
  if(d.type==='motion_error'){latest.current.onError(typeof d.message==='string'?d.message:'Movement is temporarily unavailable.');return}
  const w=latest.current.world;
  if(!w||w.city!==d.city||w.position?.zone_id!==d.input_zone)return;
  setWorld(current=>acceptMotion(current,d,d.city,d.input_zone));
  setStalled(stall.current.update(!!d.position?.blocked,Date.now()));
 },[setWorld]);
 const flush=useCallback(async()=>{
  if(inFlight.current||!pending.current)return;
  inFlight.current=true;
  try{
   while(pending.current){
    const d=pending.current;pending.current=null;
    const w=latest.current.world;
    if(transitionGate.current.paused||!transitionGate.current.accepts(d.seq)||!latest.current.enabled||w?.city!==d.city||w?.position?.zone_id!==d.zone)continue;
    try{
    const token=sessionStorage.getItem('pulse-token');
    const res=await fetch('/api'+(d.action==='drive'?'/mobility/drive':'/world/move'),{method:'POST',signal:AbortSignal.timeout(1500),headers:{'Content-Type':'application/json','X-Pulse-Client':'web',...(token?{Authorization:`Bearer ${token}`}:{})},body:JSON.stringify(d.action==='drive'?{city:d.city,zone:d.zone,steer:d.x,throttle:-d.z}:{city:d.city,zone:d.zone,dx:d.x,dz:d.z,mode:d.mode})});
    const value=await res.json();if(!res.ok)throw new Error(typeof value.detail==='string'?value.detail:'Movement unavailable');
    receive({...(value.position?value:{position:value}),type:'motion',seq:d.seq,city:d.city,input_zone:d.zone});
    }catch(e){if(transitionGate.current.accepts(d.seq))latest.current.onError((e as Error).name==='TimeoutError'?'Movement connection interrupted. Reconnecting…':(e as Error).message)}
   }
  }finally{inFlight.current=false}
 },[receive]);
 const move=useCallback((x:number,z:number)=>{
  const {world:w,mode,enabled}=latest.current;if(transitionGate.current.paused||!enabled||!w?.position||w.journey){held.current.reset();return}
  const place=w.city+':'+w.position.zone_id;if(location.current!==place){held.current.reset();location.current=place}
  const intent=w.rental?{x,z,mode:'walk'}:held.current.update(x,z,performance.now(),mode==='run');
  if(!x&&!z)setStalled(stall.current.update(false,Date.now()));
  const d={type:'input',seq:++sequence.current,city:w.city,zone:w.position.zone_id||'world',action:w.rental?'drive':'move',...intent};
  if(socket.current?.readyState===WebSocket.OPEN&&socket.current.bufferedAmount<2048){socket.current.send(JSON.stringify(d));pending.current=null;return}
  pending.current=d;void flush();
 },[flush]);
 const transition=useCallback(async(operation:()=>Promise<Data>)=>{
  const w=latest.current.world;
  if(!w||!transitionGate.current.begin(sequence.current))return;
  pending.current=null;held.current.reset();setTransitioning(true);setStalled(stall.current.update(false,Date.now()));
  try{
   const result=await operation();
   // Publish the server result to the input ref before resuming the 120ms loop.
   latest.current.world=acceptMotion(latest.current.world,result,w.city,w.position.zone_id);
   setWorld(current=>acceptMotion(current,result,w.city,w.position.zone_id));
  }finally{transitionGate.current.finish();setTransitioning(false)}
 },[setWorld]);
 return {move,receive,socket,stalled,transition,transitioning};
}
