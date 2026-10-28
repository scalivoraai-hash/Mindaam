import {BRAND} from '@/lib/brand';
import type { Metadata,Viewport } from 'next';
import './profiles.css';import ProfileOverlay from '@/components/UserProfile';
import './globals.css';import './premium.css';import './brand.css';import './living-world.css';import './theme.css';import ServiceWorker from '@/components/ServiceWorker';
export const viewport:Viewport={width:'device-width',initialScale:1,viewportFit:'cover',interactiveWidget:'resizes-content'};
export const metadata:Metadata={metadataBase:new URL(BRAND.origin),title:`${BRAND.name} · ${BRAND.tagline}`,manifest:'/manifest.webmanifest',icons:{icon:'/favicon.ico',apple:'/icon-192.png'},description:'Explore real neighbourhoods, meet your people and share little worlds together.',openGraph:{title:`${BRAND.name} · ${BRAND.tagline}`,description:'Real people. Shared places. Little worlds, together.',images:['/social-card.png']},twitter:{card:'summary_large_image',title:'Mindaam',images:['/social-card.png']}};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><ServiceWorker/>{children}<ProfileOverlay/></body></html>}
