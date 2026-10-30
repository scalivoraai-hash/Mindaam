"""Read-only conservative historical PC review. This module never writes adjustments."""
from collections import defaultdict
from sqlalchemy import select
from .models import Ledger

CLEAR_GAMEPLAY={'welcome','mission','daily','referral','collectible','fruit','gem','visit'}
def review_rows(rows):
 grouped=defaultdict(list)
 for row in rows:
  if row.currency=='credits':grouped[row.user_id].append(row)
 accounts=[]
 for user,entries in sorted(grouped.items()):
  entries.sort(key=lambda row:(row.created_at,row.id))
  value=sum(row.amount for row in entries)
  gameplay=sum(row.amount for row in entries if row.amount>0 and row.kind in CLEAR_GAMEPLAY)
  # Preserve the entire lifetime value of purchases, tickets, refunds and every
  # ambiguous credit. Attribute ALL spending to gameplay first. This deliberately
  # under-recovers rather than confiscating possibly purchased/transferred value.
  protected=sum(row.amount for row in entries if row.amount>0 and row.kind not in CLEAR_GAMEPLAY)
  candidate=max(0,min(gameplay,value-protected))
  accounts.append({'user_id':user,'current_pc':value,'historical_gameplay_pc':gameplay,'protected_or_ambiguous_lifetime_pc':protected,'candidate_pc_for_owner_review':candidate,'negative_balance':value<0})
 return {'mode':'DRY_RUN_ONLY','adjustments_applied':False,'backup_required_before_any_adjustment':True,'owner_approval_required':True,'accounts':accounts,'totals':{'accounts':len(accounts),'current_pc':sum(r['current_pc'] for r in accounts),'candidate_pc_for_owner_review':sum(r['candidate_pc_for_owner_review'] for r in accounts),'negative_balance_accounts':sum(r['negative_balance'] for r in accounts)}}

def inspect(db):return review_rows(list(db.scalars(select(Ledger).where(Ledger.currency=='credits'))))

if __name__=='__main__':
 import json
 from .db import SessionLocal
 with SessionLocal() as db:
  # Export aggregate evidence to protected job logs; no account identities.
  result=inspect(db);result.pop('accounts')
  print('MINDAAM_LEDGER_DRY_RUN '+json.dumps(result,sort_keys=True))
