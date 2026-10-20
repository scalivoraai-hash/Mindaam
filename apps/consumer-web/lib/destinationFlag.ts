const warned=new Set<string>();
/** Country metadata comes from the existing destination catalogue, never the user. */
export function destinationCountry(destination:{country_code?:string;country?:string;id?:string}){
 const code=(destination.country_code||destination.country||'').toUpperCase();
 if(/^[A-Z]{2}$/.test(code))return code;
 const key=destination.id||'unknown';if(!warned.has(key)){warned.add(key);console.warn('[destination] Missing country metadata',{destination:key});}
 return '';
}
export function destinationFlag(destination:Parameters<typeof destinationCountry>[0]){const code=destinationCountry(destination);return code?String.fromCodePoint(...[...code].map(c=>127397+c.charCodeAt(0))):'🌐'}
