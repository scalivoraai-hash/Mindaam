import * as T from 'three';

export interface Facade {id:string; name:string; x:number; z:number; owned:boolean; color:string}
export function propertyBoards(scene:T.Scene) {
  const boards=new Map<string,T.Sprite>();
  const remove=(id:string,s:T.Sprite)=>{
    scene.remove(s);s.material.map?.dispose();s.material.dispose();boards.delete(id);
  };
  const update=(rows:Facade[])=>{
    for(const [id,s] of boards) if(!rows.some(p=>p.id===id)) remove(id,s);
    for(const p of rows){
      const version=[p.name,p.owned,p.color,p.x,p.z].join('|');
      const old=boards.get(p.id);
      if(old?.userData.version===version) continue;
      if(old) remove(p.id,old);
      const canvas=document.createElement('canvas');canvas.width=512;canvas.height=112;
      const ctx=canvas.getContext('2d');if(!ctx)continue;
      ctx.fillStyle=({forest:'#204638',burgundy:'#612840'} as Record<string,string>)[p.color]||'#172a3c';
      ctx.fillRect(0,0,512,112);ctx.fillStyle='#d5efb6';ctx.fillRect(0,0,6,112);
      ctx.font='bold 34px sans-serif';ctx.fillStyle='#fff';ctx.fillText(p.name,20,48,468);
      ctx.font='24px sans-serif';ctx.fillText(p.owned?'Owned property':'Explore property',20,88);
      const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;
      const s=new T.Sprite(new T.SpriteMaterial({map:texture,depthWrite:false}));
      s.position.set(p.x,3.4,p.z);s.scale.set(4.6,1,1);
      s.userData.version=version;s.userData.cityAction=()=>window.dispatchEvent(new CustomEvent('mindaam-property',{detail:p.id}));
      scene.add(s);boards.set(p.id,s);
    }
  };
  return {update,objects:()=>Array.from(boards.values()),dispose:()=>{for(const [id,s] of boards)remove(id,s);}};
}
