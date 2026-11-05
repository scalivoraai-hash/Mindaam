'use client';
import {useState} from 'react';
import AvatarPreview from './AvatarPreview';
import {avatarCatalog,avatarPresets,normalizeAppearance,fullOutfits,type AvatarAppearance} from '../lib/avatarAppearance';
const categories=['Presets','Figure','Skin','Hair','Face','Facial Hair','Glasses','Earrings','Clothes','Tops','Headwear','Carry'];
const field:Record<string,string>={'Figure':'figure','Hair':'style','Facial Hair':'facialHair','Glasses':'glasses','Earrings':'earrings','Clothes':'bottom','Tops':'top','Headwear':'headwear','Carry':'carry'};
const skinTones=['#f4d6c1','#e7bd9d','#dca67f','#bf855e','#a56d4b','#855438','#69432e','#492d22'];
const title=(value:string)=>value==='kurti-pants'?'Kurti & Pants':value.replaceAll('-',' ').replace(/\b\w/g,c=>c.toUpperCase());
export default function AvatarStudio({initial={}}:{initial?:AvatarAppearance}){
 const [appearance,setAppearance]=useState(()=>normalizeAppearance(initial)),[category,setCategory]=useState('Presets');
 const update=(key:string,value:string)=>setAppearance(a=>({...a,[key]:value}));
 const choices=(key:string)=><div className="avatar-options">{(avatarCatalog as Record<string,string[]>)[key].map(option=><button type="button" key={option} aria-pressed={appearance[key]===option} onClick={()=>update(key,option)}>{title(option)}</button>)}</div>;
 return <section className="avatar-studio" aria-label="Mindaam Avatar Studio"><header><p className="eyebrow">YOUR LOOK</p><h3>Mindaam Avatar Studio</h3><p className="tiny">Make it yours. Every style is available to everyone.</p></header><input type="hidden" name="avatar_config" value={JSON.stringify(appearance)}/>
 <div className="avatar-studio-body"><AvatarPreview appearance={appearance}/><div className="avatar-studio-controls"><nav className="avatar-tabs" aria-label="Appearance categories">{categories.map(name=><button type="button" key={name} aria-pressed={category===name} onClick={()=>setCategory(name)}>{name}</button>)}</nav><div className="avatar-category" aria-label={category}><h4>{category}</h4>
 {category==='Presets'&&<><div className="avatar-options">{avatarCatalog.presets.map(p=><button type="button" key={p} onClick={()=>setAppearance(a=>normalizeAppearance({...a,headwear:'nothing',carry:'nothing',glasses:'none',...avatarPresets[p]}))}>{title(p)}</button>)}</div><p className="tiny">Starting looks only. Mix clothing and accessories freely.</p></>}
 {category==='Skin'&&<><div className="skin-swatches">{skinTones.map(color=><button type="button" key={color} style={{background:color}} aria-label={'Skin tone '+color} aria-pressed={appearance.skin===color} onClick={()=>update('skin',color)}/>)}</div><label>Fine tune skin<input type="color" value={appearance.skin} onChange={e=>update('skin',e.target.value)}/></label></>}
 {category==='Face'&&['face','eyes','brows','nose','mouth'].map(key=><div key={key}><h5>{title(key)}</h5>{choices(key)}</div>)}
 {field[category]&&<>{category==='Tops'&&fullOutfits.has(appearance.bottom||'')?<p className="notice">{title(appearance.bottom!)} is a coordinated outfit. Choose trousers, shorts or another separate bottom to change the top. Your previous top is kept.</p>:choices(field[category])}</>}
 {category==='Figure'&&<button type="button" disabled className="avatar-locked">Super Cool · Coming Soon</button>}
 {(['Hair','Clothes','Tops'].includes(category))&&<label>{category==='Hair'?'Hair colour':category==='Clothes'?'Bottom / outfit colour':'Top colour'}<input type="color" value={appearance[category==='Hair'?'hair':category==='Clothes'?'pants':'color']} onChange={e=>update(category==='Hair'?'hair':category==='Clothes'?'pants':'color',e.target.value)}/></label>}
 {['Clothes','Headwear'].includes(category)&&<label>Trim & accessories<input type="color" value={appearance.accent} onChange={e=>update('accent',e.target.value)}/></label>}
 </div><footer className="avatar-studio-actions"><button type="button" onClick={()=>setAppearance(normalizeAppearance(initial))}>Restore saved look</button><span className="tiny">Use Save Profile to keep your changes.</span></footer></div></div></section>
}
