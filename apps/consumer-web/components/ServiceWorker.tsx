'use client';
import {useEffect} from 'react';
export default function ServiceWorker(){useEffect(()=>{if('serviceWorker' in navigator&&window.isSecureContext)navigator.serviceWorker.register('/sw.js').catch(()=>{})},[]);return null}
