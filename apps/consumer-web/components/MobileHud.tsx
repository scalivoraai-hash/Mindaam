'use client';
import {Camera,Bike,Bus,Gift,Trophy,MapPin,MoreHorizontal,X,EyeOff,Eye,Users,Zap} from 'lucide-react';
import {Data} from '@/lib/api';

export default function MobileHud({inEvent=false,panel,onPanel,onOpen,hidden,onHidden,mode,onMode,rental,journey,onLeave,stalled,onRecover}:{inEvent?:boolean;panel:string;onPanel:(p:string)=>void;onOpen:(name:string,path?:string)=>void;hidden:boolean;onHidden:(v:boolean)=>void;mode:string;onMode:(v:string)=>void;rental?:Data;journey?:Data;onLeave:()=>void;stalled:boolean;onRecover:()=>void}){
 return <>
  <div className="mobile-hud">
   {hidden?<button className="hud-restore glass" onClick={()=>onHidden(false)}><Eye size={17}/> Show controls</button>:<>
    <button className="quick-actions-toggle glass" aria-label={panel==='quick'?'Close quick actions':'Quick actions'} aria-expanded={panel==='quick'} onClick={()=>onPanel(panel==='quick'?'':'quick')}>{panel==='quick'?<X/>:<MoreHorizontal/>}</button>
    {panel==='quick'&&<section className="quick-actions-panel glass" aria-label="Quick actions"><p className="eyebrow">QUICK ACTIONS</p>
     <button onClick={()=>{window.dispatchEvent(new Event('pulse-reset-camera'));onPanel('')}}><Camera size={18}/> Reset view</button>
     {[[Bike,'Rentals'],[Bus,'Transit'],[Gift,'Daily Drop'],[Trophy,'Leaderboard'],[MapPin,'Map'],[Users,'Crews']].filter(([,name])=>!inEvent||!['Rentals','Transit','Map'].includes(String(name))).map(([Icon,name]:any)=><button key={name} onClick={()=>onOpen(name,name==='Crews'?'/crews':undefined)}><Icon size={18}/>{name==='Leaderboard'?'Rankings':name}</button>)}
     <button onClick={()=>{onPanel('');onHidden(true)}}><EyeOff size={18}/> Hide controls</button>
    </section>}
   </>}
   {!rental&&!journey&&<button className="mobile-run glass" aria-label={mode==='run'?'Switch to walking':'Switch to running'} aria-pressed={mode==='run'} onClick={()=>onMode(mode==='run'?'walk':'run')}><Zap size={17}/>{mode==='run'?'Run':'Walk'}</button>}
  </div>
  {journey&&<section className="compact-journey glass" aria-label="Current journey"><button onClick={()=>onOpen('Transit')}><Bus size={18}/><span>{journey.route_number||journey.route?.number||'Transit'} → {journey.destination_name||journey.destination||journey.route?.destination?.replaceAll('-',' ')||'Your destination'}<small>View journey & passengers</small></span></button><button onClick={onLeave}>Leave journey</button></section>}
  {stalled&&!rental&&!journey&&<button className="stuck-recovery glass" onClick={onRecover}>Having trouble moving? · Unstuck</button>}
 </>;
}
