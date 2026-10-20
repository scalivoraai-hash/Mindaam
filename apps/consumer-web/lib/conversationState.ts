type Session=Record<string,any>;
// Older HTTP fallbacks must not resurrect pending requests after a realtime acceptance.
export function reconcileSessions(previous:Session[],incoming:Session[]):Session[]{
 const old=new Map(previous.map(s=>[s.id,s]));const rank=(s:string)=>s==='pending'?0:s==='accepted'?1:2;
 return incoming.map(next=>{const before=old.get(next.id);if(!before)return next;const a=before.revision||before.created_at||0,b=next.revision||next.created_at||0;return a>b||(a===b&&rank(before.state)>rank(next.state))?before:next});
}
