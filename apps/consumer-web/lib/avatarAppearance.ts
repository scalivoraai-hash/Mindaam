import catalog from '../../../shared/avatar-catalog.json' with {type:'json'};
export {catalog as avatarCatalog};
export type AvatarAppearance=Record<string,string|undefined>;
export const avatarDefaults:AvatarAppearance={version:'2',figure:'classic',style:'short',face:'oval',eyes:'almond',brows:'natural',nose:'classic',mouth:'natural',facialHair:'none',glasses:'none',earrings:'none',bottom:'trousers',top:'hoodie',headwear:'nothing',carry:'nothing',color:'#ed945d',skin:'#bf855e',hair:'#302821',pants:'#29485d',accent:'#e8d9b9'};
export function normalizeAppearance(input:AvatarAppearance={}):AvatarAppearance {
 const result:AvatarAppearance={...avatarDefaults,...input,version:'2'};
 if(input.style==='cap'){result.style='short';result.headwear=input.headwear||'cap'}
 for(const [key,options] of Object.entries(catalog))if(key!=='presets'&&!options.includes(result[key]||''))result[key]=avatarDefaults[key];
 return result;
}
export const fullOutfits=new Set(['saree','half-saree','abaya','frock','kurti-pants','dungarees']);
export const avatarPresets:Record<string,AvatarAppearance>={
 boy:{top:'t-shirt',bottom:'jeans',style:'short'},girl:{top:'plain-shirt',bottom:'jeans',style:'ponytail'},
 tourist:{top:'beach-shirt',bottom:'shorts',headwear:'sun-hat',carry:'camera'},student:{top:'hoodie',bottom:'jeans',carry:'backpack'},
 farmer:{top:'collared-shirt',bottom:'mundu',headwear:'sun-hat'},office:{top:'waistcoat',bottom:'trousers',glasses:'glasses'},
 elder:{top:'kurta',bottom:'trousers',hair:'#c6c5be',glasses:'round-shades'},sporty:{top:'sports-tee',bottom:'track-pants',headwear:'cap-backwards'}
};
export function appearanceFromForm(form:FormData,previous:AvatarAppearance={}):AvatarAppearance{
 const saved=form.get('avatar_config');
 if(typeof saved==='string'&&saved){try{return normalizeAppearance(JSON.parse(saved))}catch{throw Error('Your appearance could not be read. Reopen Avatar Studio.')}}
 return {...previous,...Object.fromEntries(['color','skin','hair','pants','style'].filter(k=>form.has(k)).map(k=>[k,String(form.get(k))]))};
}
