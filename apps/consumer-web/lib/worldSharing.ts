export const growthCopy={hero:'Your City Is Alive.',headline:'Bring your people. Open your next world.',cta:'Share & Unlock',subtext:'Four share actions unlock permanent access. No sign-ups required.'};
export type InviteStyle='curious'|'hype'|'together';
export function inviteCopy(city:string,url:string,style:InviteStyle='curious'){
 if(style==='hype')return `${city} is inside Mindaam 👀\n\nExplore the city, meet people and join live experiences.\nI'm opening my next world. Come explore with me 🌍\n\n${url}`;
 if(style==='together')return `🌍 Come into Mindaam with me 👀\n\nEnter real-world-inspired cities, see who's exploring, meet people, join events and discover places together.\n\nI'm heading to ${city}. Come find me:\n${url}`;
 return `👀 I found something different.\n\nMindaam lets you step into real-world-inspired cities, see who's there, meet people, join live events, explore places and travel together.\n\nMy next stop: ${city} 🌍\nCome find me:\n${url}`;
}
export function shareUrl(channel:string,text:string,url:string){
 const t=encodeURIComponent(text),u=encodeURIComponent(url);
 if(channel==='whatsapp')return `https://wa.me/?text=${t}`;
 if(channel==='facebook')return `https://www.facebook.com/sharer/sharer.php?u=${u}`;
 if(channel==='x')return `https://twitter.com/intent/tweet?text=${encodeURIComponent('Your city is live. 👀 Explore real-world-inspired places, meet people and join live experiences on Mindaam. Come find me 🌍')}&url=${u}`;
 if(channel==='email')return `mailto:?subject=${encodeURIComponent('Come explore Mindaam with me 🌍')}&body=${t}`;
 if(channel==='sms')return `sms:?body=${encodeURIComponent('👀 Explore cities, meet people and see who’s there on Mindaam. Come find me 🌍 '+url)}`;
 return '';
}
export function progressCopy(city:string,n:number){return n>=4?`🎉 ${city} is yours.`:n===3?`One more share opens ${city}.`:n===2?'Halfway there. 2 to go.':n===1?'Nice start. 3 more shares.':`Bring your people — 4 shares unlock ${city}.`}
