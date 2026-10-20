import * as T from 'three';
import {Data} from '@/lib/api';
/** Two existing lights, one reusable canvas texture, no shadows or render targets. */
export function auditoriumScene(group:T.Group|null){
 const lights:T.SpotLight[]=[],beams:T.Mesh[]=[],leds:T.Mesh[]=[];
 group?.traverse(o=>{if(o instanceof T.SpotLight)lights.push(o);if(o instanceof T.Mesh&&o.userData.stageBeam)beams.push(o);if(o instanceof T.Mesh&&o.userData.stageLed)leds.push(o)});
 const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=576;const c=canvas.getContext('2d')!,texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;
 let signature='';const target=new T.Vector3(),direction=new T.Vector3(),up=new T.Vector3(0,1,0);const colours=[new T.Color(),new T.Color()];
 const palettes:Record<string,string[]>={STANDARD:['#9ca8ff','#8fe4e7'],CONCERT:['#8b22ff','#00dfff'],'DJ PARTY':['#ff16bf','#00e6ff'],CINEMA:['#6b86b8','#7589b9'],WARM:['#ffd7a0','#e6b882'],COOL:['#8de6ef','#8baaff'],'PURPLE WAVE':['#a819ff','#ff28b8'],'BLUE WAVE':['#1262ff','#00deff'],SPOTLIGHT:['#fff0cd','#a5cde5'],PULSE:['#a794e9','#78d3e3'],RAINBOW:['#a594e7','#62d3b5']};
 function line(text:string,y:number,size:number,maxLines:number){c.font=`${size>28?'bold ':''}${size}px sans-serif`;let row='',n=0;for(const word of text.split(/\s+/)){const next=row?row+' '+word:word;if(c.measureText(next).width>875&&row){c.fillText(row,74,y+n*size*1.25);n++;row=word;if(n>=maxLines)return}else row=next}if(n<maxLines)c.fillText(row,74,y+n*size*1.25,875)}
 const update=(event:Data,seconds:number,dt:number)=>{
  const next=JSON.stringify([event.title,event.description,event.status]);
  if(next!==signature){signature=next;const bg=c.createLinearGradient(0,0,1024,576);bg.addColorStop(0,'#143b53');bg.addColorStop(.56,'#202b51');bg.addColorStop(1,'#603d72');c.fillStyle=bg;c.fillRect(0,0,1024,576);c.fillStyle='#79e6e1';c.font='bold 26px sans-serif';c.fillText('MINDAAM LIVE',74,92);c.fillStyle='#f2f7ff';line(event.title||'Your city. Your stage.',205,56,2);c.fillStyle='#d0ddef';line(event.description||'Conversations, ideas and shared moments.',367,28,3);c.fillStyle='#b9ec9a';c.font='21px sans-serif';c.fillText(event.status==='live'?'● LIVE EVENT · STAGE READY':'YOUR EVENT STARTS HERE',74,522);texture.needsUpdate=true}
  const state=event.presentation?.lighting||event.lighting||{},preset=state.preset||'STANDARD',palette=palettes[preset]||palettes.STANDARD,intensity=state.enabled===false?0:Number(state.intensity??.7);
  const phase=seconds*.45,pulse=preset==='PULSE'?.84+.16*Math.sin(phase):1,blend=1-Math.exp(-dt*2.5);
  lights.forEach((light,i)=>{colours[i].set(palette[i%2]);if(preset==='RAINBOW')colours[i].setHSL((seconds/45+i*.2)%1,.85,.56);light.color.lerp(colours[i],blend);light.intensity+=(145*intensity*pulse*(preset==='CINEMA'?.3:1)-light.intensity)*blend;const z=state.target==='audience'?4:state.target==='screen'?-13:-10;const sweep=preset.endsWith('WAVE')||preset==='DJ PARTY'?Math.sin(phase+i)*2:0;light.target.position.lerp(target.set((i?3:-3)+sweep,state.target==='screen'?3:.6,z),blend)});
  beams.forEach(beam=>{const light=beam.userData.stageBeam as T.SpotLight;direction.copy(light.position).sub(light.target.position);const length=direction.length();beam.position.copy(light.position).add(light.target.position).multiplyScalar(.5);beam.scale.set(1,length,1);beam.quaternion.setFromUnitVectors(up,direction.normalize());const m=beam.material as T.ShaderMaterial;m.uniforms.beamColour.value.copy(light.color);m.uniforms.strength.value=(preset==='CINEMA'?.045:.3)*intensity*pulse});
  leds.forEach(led=>{const light=led.userData.stageLed as T.SpotLight;led.position.copy(light.position);led.lookAt(light.target.position);(led.material as T.MeshBasicMaterial).color.copy(light.color)});
 };
 return {texture,update,dispose:()=>texture.dispose()};
}
