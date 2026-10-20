'use client';
import {useState} from 'react';
import {Globe2} from 'lucide-react';
import {destinationCountry} from '@/lib/destinationFlag';
const bundled=new Set(['AE','AU','CA','CN','DE','ES','FR','GB','IE','IN','IT','JP','KR','NL','QA','SA','SG','TH','US']);
/** Small local flag-icons 7.5.0 SVGs, independent of platform emoji support. */
export default function CountryFlag({destination}:{destination:Parameters<typeof destinationCountry>[0]}){
 const code=destinationCountry(destination),[failed,setFailed]=useState('');
 return bundled.has(code)&&failed!==code?<img className="country-flag" src={'/flags/'+code.toLowerCase()+'.svg'} alt={code+' flag'} width={24} height={18} onError={()=>{console.warn('[destination] Flag asset unavailable',{country:code});setFailed(code)}}/>:<Globe2 className="country-flag" role="img" aria-label={code||'World'} size={20}/>;
}
