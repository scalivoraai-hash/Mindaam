import type { Metadata,Viewport } from 'next';
import './globals.css';import './premium.css';import ServiceWorker from '@/components/ServiceWorker';
export const viewport:Viewport={width:'device-width',initialScale:1,viewportFit:'cover',interactiveWidget:'resizes-content'};
export const metadata:Metadata={metadataBase:new URL('https://pulseworld-production.up.railway.app'),title:'MyLilWorlds · Your City. Alive.',manifest:'/manifest.webmanifest',icons:{icon:'/icon.svg',apple:'/icon-192.png'},description:'Explore real neighbourhoods, meet your people and share little worlds together.',openGraph:{title:'MyLilWorlds · Your City. Alive.',description:'Real people. Shared places. Little worlds, together.',images:['/social-card.png']},twitter:{card:'summary_large_image',title:'MyLilWorlds',images:['/social-card.png']}};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><ServiceWorker/>{children}</body></html>}
