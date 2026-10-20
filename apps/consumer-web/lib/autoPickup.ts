type Position={x:number,z:number};
type Item=Position & {id:string,kind:string};
// Server positions are virtual metres. At most one request can be pending.
export class PickupGate {
 private pending:string|null=null;
 private completed=new Set<string>();
 private retryAt=new Map<string,number>();
 nearest(position:Position|undefined,items:Item[],now=Date.now()):Item|undefined {
  if(!position||this.pending)return;
  return items.filter(item=>(item.kind==='fruit'||item.kind==='gem')&&!this.completed.has(item.id)&&(this.retryAt.get(item.id)||0)<=now&&Math.hypot(position.x-item.x,position.z-item.z)<=2)
   .sort((a,b)=>Math.hypot(position.x-a.x,position.z-a.z)-Math.hypot(position.x-b.x,position.z-b.z))[0];
 }
 begin(id:string,now=Date.now()):boolean {
  if(this.pending||this.completed.has(id)||(this.retryAt.get(id)||0)>now)return false;
  this.pending=id;return true;
 }
 finish(id:string,success:boolean,now=Date.now()){
  if(this.pending===id)this.pending=null;
  if(success){this.completed.add(id);this.retryAt.delete(id)}
  else this.retryAt.set(id,now+8000);
 }
}
