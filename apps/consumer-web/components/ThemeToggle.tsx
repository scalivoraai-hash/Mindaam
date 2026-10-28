'use client';
import {useEffect,useState} from 'react';
import {Sun,Moon} from 'lucide-react';
export const THEME_KEY='mindaam-theme';
export function ThemeRuntime(){
 useEffect(()=>{
  const system=matchMedia('(prefers-color-scheme: light)');
  const sync=()=>{let saved:string|null=null;try{saved=localStorage.getItem(THEME_KEY)}catch{}document.documentElement.dataset.theme=saved==='light'||saved==='dark'?saved:system.matches?'light':'dark';window.dispatchEvent(new Event('mindaam-theme-change'))};
  const storage=(e:StorageEvent)=>{if(e.key===THEME_KEY||e.key===null)sync()};
  sync();system.addEventListener('change',sync);window.addEventListener('storage',storage);
  return()=>{system.removeEventListener('change',sync);window.removeEventListener('storage',storage)};
 },[]);return null;
}
export default function ThemeToggle(){
 const [theme,setTheme]=useState('dark');
 useEffect(()=>{const read=()=>setTheme(document.documentElement.dataset.theme||'dark');read();window.addEventListener('mindaam-theme-change',read);return()=>window.removeEventListener('mindaam-theme-change',read)},[]);
 return <button type="button" className="theme-toggle" aria-label="Light theme" aria-pressed={theme==='light'} title={theme==='dark'?'Switch to Premium Light':'Switch to Immersive Dark'} onClick={()=>{const next=theme==='dark'?'light':'dark';document.documentElement.dataset.theme=next;try{localStorage.setItem(THEME_KEY,next)}catch{}window.dispatchEvent(new Event('mindaam-theme-change'))}}><Sun size={16}/><Moon size={16}/><span className="sr-only">{theme==='dark'?'Immersive Dark':'Premium Light'}</span></button>;
}
