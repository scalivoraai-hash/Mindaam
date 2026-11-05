import catalog from '../../../shared/city-street-furniture.json' with {type:'json'};
type Feature={id:string;osm_id:string;tags:Record<string,string>;points:number[][]};
/** Separate visual data: immutable collision/geography cache hashes stay unchanged. */
export async function loadCityStreetFurniture(city:string):Promise<Feature[]>{
 const entry=(catalog as Record<string,{path:string;sha256:string;nodes:number}>)[city];if(!entry)return [];
 try{const response=await fetch(entry.path,{cache:'force-cache',signal:AbortSignal.timeout(4000)});if(!response.ok)return [];const buffer=await response.arrayBuffer();const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer)),v=>v.toString(16).padStart(2,'0')).join('');if(hash!==entry.sha256)return [];const data=JSON.parse(new TextDecoder().decode(buffer));return data.city===city&&Array.isArray(data.features)&&data.features.length===entry.nodes?data.features:[]}catch{return []}
}
