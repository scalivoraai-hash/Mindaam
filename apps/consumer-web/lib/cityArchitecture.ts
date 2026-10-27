/** Original regional colour archetypes, not a surveyed facade reconstruction. */
export type ArchitectureRegion='british'|'gulf'|'indian'|'north-american'|'international';
export function architectureRegion(city:string):ArchitectureRegion{
 if(/^(london|birmingham|milton-keynes|manchester|leeds|liverpool|edinburgh|glasgow|bristol|cardiff|belfast|nottingham|oxford|cambridge)(-|$)/.test(city))return 'british';
 if(/^(dubai|abu-dhabi|sharjah|doha|riyadh|jeddah)(-|$)/.test(city))return 'gulf';
 if(/^(mumbai|delhi|new-delhi|bengaluru|bangalore|chennai|hyderabad|kolkata|kochi|pune|ahmedabad)(-|$)/.test(city))return 'indian';
 if(/^(new-york|chicago|los-angeles|san-francisco|toronto)(-|$)/.test(city))return 'north-american';
 return 'international';
}
const walls:Record<ArchitectureRegion,string[]>={british:['#b78368','#d6c5a9','#a4715e','#ddd4c3','#bf977d','#c9b29a','#b7bebd','#d8c5b1'],gulf:['#e6d6b8','#dbc7a5','#d5dee0','#d5b88c','#eee1c8','#c5ccd0','#c9b99e','#ddd5ca'],indian:['#d6bfa2','#d4bda9','#cad0b8','#e4ceb0','#cbb3ad','#bfd1cd','#d7d4c8','#d6c4a0'],'north-american':['#a87861','#c0b6a4','#ba876e','#c5c6c4','#b49982','#c2ac91','#aab9c0','#c5b8aa'],international:['#e0d2bc','#b98e76','#cbd5d5','#c7baa7','#e5ceb5','#d6b69f','#bccbd0','#d0c5ba']};
export function regionalPalette(city:string,index:number,base:{wall:string;trim:string;roof:string;accent:string},tags:Record<string,string>){
 const region=architectureRegion(city),palette={...base,wall:walls[region][Math.abs(index)%8]};
 // A literal mapped hex colour overrides archetypes; no CSS or URLs are accepted.
 const mapped=tags['building:colour']||tags['building:color'];if(mapped&&/^#[0-9a-f]{6}$/i.test(mapped))palette.wall=mapped;
 if(region==='gulf'){palette.trim='#f0e5d0';palette.roof='#b8ac96'}
 if(region==='north-american')palette.trim='#ded7c8';
 return palette;
}
