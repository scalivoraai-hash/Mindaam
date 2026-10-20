import type {Metadata} from 'next';
import {RequestLanding} from '@/components/DestinationDemand';
export const metadata:Metadata={title:'Bring MyLilWorlds to your city',description:'Help choose the next MyLilWorlds destination. Add your interest and invite your people.',openGraph:{title:'Your city could be next. MyLilWorlds.',description:'Explore. Meet. Talk. Play. Help bring MyLilWorlds here.',images:['/social-card.png']},twitter:{card:'summary_large_image',images:['/social-card.png']}};
export default async function Page({params}:{params:Promise<{code:string}>}){const {code}=await params;return <RequestLanding code={code}/>}
