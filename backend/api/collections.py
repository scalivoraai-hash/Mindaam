"""Inventory and rankings derived from committed claims and immutable ledger entries."""
import time
from collections import Counter
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from .auth import current_user
from .db import get_db
from .models import Claim,Collectible,Ledger,User,Mission,MissionCompletion
router=APIRouter(prefix='/api')
@router.get('/inventory')
def inventory(period:str='all',u=Depends(current_user),db=Depends(get_db)):
 if period not in ['today','all']:raise HTTPException(422,'Invalid period')
 since=int(time.time()//86400)*86400 if period=='today' else 0
 rows={}
 for claim,c in db.execute(select(Claim,Collectible).join(Collectible,Collectible.id==Claim.collectible_id).where(Claim.user_id==u.id,Claim.created_at>=since)):
  key=(c.kind,c.title);r=rows.setdefault(key,dict(kind=c.kind,title=c.title,count=0,xp=0));r['count']+=1;r['xp']+=5 if c.kind=='fruit' else 15
 totals=Counter()
 for l in db.scalars(select(Ledger).where(Ledger.user_id==u.id,Ledger.created_at>=since,Ledger.amount>0,Ledger.kind.in_(['collectible','mission']))):totals[l.currency]+=l.amount
 completed=db.scalars(select(MissionCompletion).where(MissionCompletion.user_id==u.id)).all()
 return dict(period=period,items=list(rows.values()),total=sum(r['count'] for r in rows.values()),xp=totals['xp'],credits=totals['credits'],badges=[{'title':m.title,'earned_at':c.created_at} for c in completed if (m:=db.get(Mission,c.mission_id))])
@router.get('/rankings')
def rankings(scope:str='local',city:str='milton-keynes',period:str='week',metric:str='xp',u=Depends(current_user),db=Depends(get_db)):
 if scope not in ['local','city','uk'] or period not in ['today','week','month','all'] or metric not in ['xp','credits','missions','collections']:raise HTTPException(422,'Invalid ranking filter')
 seconds={'today':86400,'week':604800,'month':2592000,'all':1e12}[period];since=time.time()-seconds
 users={p.id:p for p in db.scalars(select(User).where(User.suspended==False,User.privacy=='City Mode'))};scores=Counter()
 def included(c):return scope=='uk' or (scope=='city' and city.startswith('milton-keynes') and c.startswith('milton-keynes')) or c==city
 for claim,c in db.execute(select(Claim,Collectible).join(Collectible,Collectible.id==Claim.collectible_id).where(Claim.created_at>=since)):
  if claim.user_id in users and included(c.city) and metric in ['xp','collections']:scores[claim.user_id]+=1 if metric=='collections' else 5 if c.kind=='fruit' else 15
 for mc,m in db.execute(select(MissionCompletion,Mission).join(Mission,Mission.id==MissionCompletion.mission_id).where(MissionCompletion.created_at>=since)):
  if mc.user_id in users and included(m.city) and metric!='collections':scores[mc.user_id]+=1 if metric=='missions' else m.credits if metric=='credits' else m.xp
 ordered=scores.most_common()
 own=next(({'rank':i+1,'id':id,'username':users[id].username,'score':score} for i,(id,score) in enumerate(ordered) if id==u.id),None)
 return {'own':own,'scope':scope,'metric':metric,'period':period,'notice':'Earned collection and mission activity only; excludes purchases, transfers and daily grants.','rows':[{'id':id,'username':users[id].username,'score':score} for id,score in scores.most_common(50)]}
