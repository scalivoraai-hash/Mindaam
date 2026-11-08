import * as T from 'three';
import {buildingSignSpecs,type SignSpec} from './BuildingSigns.ts';

export interface Facade {id:string; name:string; x:number; z:number; owned:boolean; color:string;colors?:Record<string,string>}
type Feature={id:string;tags:Record<string,string>;points:number[][]};
export function propertyFrontages(features:Feature[],city:string){
  const buildings=new Map(features.filter(f=>f.tags.building).map(f=>[city+':'+f.id,f]));
  const roads=features.filter(f=>f.tags.highway);
  const cache=new Map<string,SignSpec|undefined>();
  return (p:Facade)=>{
    if(!cache.has(p.id)){
      const f=buildings.get(p.id);
      cache.set(p.id,f?buildingSignSpecs([...roads,{...f,tags:{...f.tags,name:p.name}}])[0]:undefined);
    }
    return cache.get(p.id);
  };
}
export function propertyBoards(scene:T.Scene,tint:(id:string,colors:Record<string,string>)=>void,features:Feature[]=[],city='') {
  const frontage=propertyFrontages(features,city);
  const boards=new Map<string,T.Sprite|T.Mesh<T.PlaneGeometry,T.MeshBasicMaterial>>();
  const remove=(id:string,s:T.Sprite|T.Mesh<T.PlaneGeometry,T.MeshBasicMaterial>)=>{
    tint(id,{});scene.remove(s);s.material.map?.dispose();s.material.dispose();if(s instanceof T.Mesh)s.geometry.dispose();boards.delete(id);
  };
  const update=(rows:Facade[])=>{
    for(const [id,s] of boards) if(!rows.some(p=>p.id===id)) remove(id,s);
    for(const p of rows){
      const version=[p.name,p.owned,p.color,JSON.stringify(p.colors),p.x,p.z].join('|');
      const old=boards.get(p.id);
      if(old?.userData.version===version) continue;
      if(old) remove(p.id,old);
      if(p.colors)tint(p.id,p.colors);
      const canvas=document.createElement('canvas');canvas.width=512;canvas.height=112;
      const ctx=canvas.getContext('2d');if(!ctx)continue;
      ctx.fillStyle=({forest:'#204638',burgundy:'#612840'} as Record<string,string>)[p.color]||'#172a3c';
      ctx.fillRect(0,0,512,112);ctx.fillStyle='#d5efb6';ctx.fillRect(0,0,6,112);
      ctx.font='bold 34px sans-serif';ctx.fillStyle='#fff';ctx.fillText(p.name,20,48,468);
      ctx.font='24px sans-serif';ctx.fillText(p.owned?'Owned property':'Explore property',20,88);
      const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;
      // The persisted inventory anchor may be a rear edge. Attach the visual
      // board to the existing street-facing facade, above its original sign.
      // A wall-aligned plane cannot rotate halfway through the building.
      const anchor=frontage(p);
      const s=anchor?new T.Mesh(new T.PlaneGeometry(1,1),new T.MeshBasicMaterial({map:texture,depthWrite:false})):
        new T.Sprite(new T.SpriteMaterial({map:texture,depthWrite:false}));
      s.position.set(anchor?.x??p.x,4.2,anchor?.z??p.z);s.scale.set(Math.min(4.6,anchor?.width??4.6),1,1);
      if(anchor)s.rotation.y=anchor.angle;
      s.userData.version=version;s.userData.cityAction=()=>window.dispatchEvent(new CustomEvent('mindaam-property',{detail:p.id}));
      scene.add(s);boards.set(p.id,s);
    }
  };
  return {update,objects:()=>Array.from(boards.values()),dispose:()=>{for(const [id,s] of boards)remove(id,s);}};
}
