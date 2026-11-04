import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {cinematicCharacterFactory} from './CinematicCharacter';
import {human} from './WorldAssets';

/** Optional staging asset. Any network, integrity or rig failure retains the standard avatar. */
export async function loadCinematicCharacter(){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),4000);
 try{
  const response=await fetch('/assets/whitehouse/character-5f945139.glb',{signal:controller.signal,cache:'force-cache'});
  if(!response.ok)throw Error('Character asset unavailable');
  const data=await response.arrayBuffer();
  if(data.byteLength!==1922556)throw Error('Character asset size mismatch');
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)),v=>v.toString(16).padStart(2,'0')).join('');
  if(hash!=='5f945139ffd86cbd4f8877784412adb97c388eb10b65eda931983eb716ea375e')throw Error('Character asset integrity mismatch');
  const asset=await new GLTFLoader().parseAsync(data,'');
  return cinematicCharacterFactory(asset.scene,human);
 }finally{clearTimeout(timer)}
}
