"""Read-only conservative historical PC review. This module never writes adjustments."""
from collections import defaultdict
import hashlib,json
from sqlalchemy import select
from .models import Ledger

CLEAR_GAMEPLAY={'welcome','mission','daily','referral','collectible','fruit','gem','visit'}
def review_rows(rows, verified_purchase_ids=()):
 grouped=defaultdict(list)
 debits=defaultdict(list)
 for row in rows:
  if row.currency=='credits' and row.kind=='event_ticket' and row.amount<0 and getattr(row,'source',None):debits[(row.source,-row.amount)].append(row.user_id)
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
  kinds=defaultdict(int);running=0;consistent=True
  for row in entries:
   kinds[row.kind]+=row.amount
   consistent=consistent and getattr(row,'previous_balance',running)==running and getattr(row,'balance',running+row.amount)==running+row.amount
   running+=row.amount
  verified=sum(row.amount for row in entries if row.amount>0 and row.kind=='purchase' and row.id in verified_purchase_ids)
  fingerprint=hashlib.sha256(json.dumps([(r.id,r.amount,r.kind,getattr(r,'source',''),getattr(r,'idempotency_key',''),getattr(r,'previous_balance',None),getattr(r,'balance',None)) for r in entries],separators=(',',':')).encode()).hexdigest()
  accounts.append({'account_ref':hashlib.sha256(user.encode()).hexdigest()[:24],'ledger_sha256':fingerprint,'ledger_entries':len(entries),'ledger_balance_consistent':consistent,'verified_purchase_pc':verified,'purchase_ledger_pc':sum(r.amount for r in entries if r.amount>0 and r.kind=='purchase'),'conserved_ticket_sale_pc':sum(r.amount for r in entries if r.amount>0 and r.kind=='event_ticket_sale' and len(debits.get((getattr(r,'source',None),r.amount),[]))==1 and debits[(r.source,r.amount)][0]!=user),'ticket_sale_ledger_pc':sum(r.amount for r in entries if r.amount>0 and r.kind=='event_ticket_sale'),'refund_ledger_pc':sum(r.amount for r in entries if r.amount>0 and 'refund' in r.kind),'adjustment_net_pc':sum(r.amount for r in entries if 'adjust' in r.kind),'legacy_test_promotional_pc':sum(r.amount for r in entries if r.amount>0 and r.kind in {'test','test_credit','seed','promo','promotion','promotional'}),'net_pc_by_kind':dict(sorted(kinds.items())),'proposed_pc':value-candidate,'user_id':user,'current_pc':value,'historical_gameplay_pc':gameplay,'protected_or_ambiguous_lifetime_pc':protected,'candidate_pc_for_owner_review':candidate,'negative_balance':value<0})
 return {'mode':'DRY_RUN_ONLY','adjustments_applied':False,'backup_required_before_any_adjustment':True,'owner_approval_required':True,'accounts':accounts,'totals':{'accounts':len(accounts),'affected_accounts':sum(r['candidate_pc_for_owner_review']>0 for r in accounts),'proposed_pc':sum(r['proposed_pc'] for r in accounts),'inconsistent_accounts':sum(not r['ledger_balance_consistent'] for r in accounts),'current_pc':sum(r['current_pc'] for r in accounts),'candidate_pc_for_owner_review':sum(r['candidate_pc_for_owner_review'] for r in accounts),'negative_balance_accounts':sum(r['negative_balance'] for r in accounts)}}

def inspect(db):
 from sqlalchemy import text
 rows=list(db.scalars(select(Ledger).where(Ledger.currency=='credits')))
 payments={r['id']:r for r in db.execute(text("SELECT id,user_id,credits,status,provider_id FROM payments")).mappings()}
 verified={r.id for r in rows if r.kind=='purchase' and (p:=payments.get(r.source)) and p['user_id']==r.user_id and p['status']=='paid' and p['provider_id'] and p['credits']==r.amount and r.idempotency_key=='payment:'+p['id']}
 return review_rows(rows,verified)


if __name__=='__main__':
 import json
 from .db import SessionLocal
 with SessionLocal() as db:
  # Export aggregate evidence to protected job logs; no account identities.
  result=inspect(db);result.pop('accounts')
  print('MINDAAM_LEDGER_DRY_RUN '+json.dumps(result,sort_keys=True))
