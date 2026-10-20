export type BuildingFamily='home'|'apartments'|'shop'|'office'|'civic'|'utility'|'neutral';
/** Unknown OSM buildings remain neutral; a palette never invents a business/use. */
export function buildingStyle(tags:Record<string,string>,id:string){
 const hash=Array.from(id).reduce((h,c)=>(h*31+c.charCodeAt(0))>>>0,7);
 const type=tags.building||'',use=tags['building:use']||type;
 let family:BuildingFamily='neutral';
 if(['house','detached','semidetached_house','terrace','bungalow','residential','townhouse'].includes(use))family='home';
 if(['apartments','dormitory','hotel'].includes(use))family='apartments';
 if(['commercial','retail','supermarket','kiosk'].includes(use)||tags.shop||['cafe','restaurant','pub','fast_food','bank','pharmacy'].includes(tags.amenity))family='shop';
 if(use==='office'||tags.office)family='office';
 if(['civic','public','church','cathedral','school','hospital','train_station'].includes(use)||['community_centre','theatre','library','townhall','school','hospital'].includes(tags.amenity))family='civic';
 if(['industrial','warehouse','garages','shed'].includes(use))family='utility';
 const declared=parseFloat(tags.height)||parseFloat(tags['building:levels']||'')*3.1;
 const height=Math.min(60,Math.max(3,declared||({home:type==='bungalow'?3.4:6.2,apartments:15.5,shop:7,office:18.6,civic:9.3,utility:5.4,neutral:6.2}[family])));
 return {family,height,palette:hash%8,variant:hash%3,hash,roof:tags['roof:shape']||(family==='home'?'gabled':'flat'),atlas:family==='office'?2:family==='utility'?3:family==='apartments'?1:0};
}
