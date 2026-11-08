"""Audited profile corrections and provider-backed recovery of an existing payment.

No checkout, payment capture, price change or arbitrary PC issuance is permitted.
"""
import hashlib,json,os,time
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import select,func
from .db import get_db
from .core import Strict,serialize
from .models import User,Ledger,Audit
from .operations import super_admin,audit
from .profile_schema import ProfileUpdate
from .commerce import Payment
from .economy import credit

router=APIRouter(prefix='/api/super-admin')
EDITABLE={'display_name','bio','languages','theme'}

class ProfileCorrection(Strict):
    expected:dict
    profile:ProfileUpdate
    reason:str=Field(min_length=12,max_length=500)

@router.patch('/users/{user_id}/profile')
def correct_profile(user_id:str,data:ProfileCorrection,u=Depends(super_admin),db=Depends(get_db)):
    changes=data.profile.model_dump(exclude_unset=True)
    if not changes or not set(changes)<=EDITABLE or not set(data.expected)<=EDITABLE:
        raise HTTPException(422,'Only display name, biography, languages and theme can be corrected here')
    if len(data.reason.strip())<12:raise HTTPException(422,'Document the correction reason')
    person=db.scalar(select(User).where(User.id==user_id).with_for_update().execution_options(populate_existing=True))
    if not person:raise HTTPException(404,'User not found')
    if person.role in {'admin','super_admin'}:raise HTTPException(409,'Privileged profiles require separate review')
    before={k:v for k,v in (person.profile or {}).items() if k in EDITABLE}
    if before!=data.expected:raise HTTPException(409,'Profile changed. Refresh and review before saving')
    changes={k:v.strip() if isinstance(v,str) else v for k,v in changes.items()}
    person.profile={**(person.profile or {}),**changes}
    audit(db,u,'user.profile_corrected',user_id,{'before':before,'changes':changes,'reason':data.reason.strip()})
    return {'profile':{k:v for k,v in person.profile.items() if k in EDITABLE}}

def provider_checkout(provider_id):
    import stripe
    live=os.getenv('APP_ENV','local')=='production'
    key=os.getenv('STRIPE_SECRET_KEY','')
    if not key.startswith(('sk_live_','rk_live_') if live else ('sk_test_','rk_test_')):
        raise HTTPException(503,'A matching Stripe credential is required for purchase verification')
    try:
        client=stripe.StripeClient(key,max_network_retries=1,http_client=stripe.RequestsClient(timeout=8))
        return client.v1.checkout.sessions.retrieve(provider_id,{'expand':['payment_intent.latest_charge']}).to_dict_recursive()
    except stripe.StripeError:
        raise HTTPException(502,'The payment provider could not verify this purchase. No credits were changed')

def verify_receipt(payment,receipt):
    live=os.getenv('APP_ENV','local')=='production'
    intent=receipt.get('payment_intent')
    charge=intent.get('latest_charge') if isinstance(intent,dict) else None
    valid=(receipt.get('id')==payment.provider_id and receipt.get('livemode') is live
        and receipt.get('mode')=='payment' and receipt.get('status')=='complete'
        and receipt.get('payment_status')=='paid' and receipt.get('amount_total')==payment.amount_pence
        and receipt.get('currency')=='gbp' and receipt.get('metadata',{}).get('payment_id')==payment.id
        and isinstance(intent,dict) and intent.get('status')=='succeeded'
        and isinstance(intent.get('id'),str) and intent['id'].startswith('pi_')
        and (not payment.intent_id or payment.intent_id==intent['id'])
        and intent.get('amount_received')==payment.amount_pence and intent.get('currency')=='gbp'
        and intent.get('livemode') is live and isinstance(charge,dict)
        and isinstance(charge.get('id'),str) and charge['id'].startswith('ch_')
        and charge.get('paid') is True and charge.get('captured') is True
        and charge.get('amount')==payment.amount_pence and charge.get('currency')=='gbp'
        and charge.get('payment_intent')==intent['id'] and charge.get('livemode') is live
        and charge.get('amount_refunded')==0 and charge.get('refunded') is False
        and charge.get('disputed') is False)
    if not valid:raise HTTPException(409,'A matching captured, unrefunded and undisputed purchase could not be verified')
    return {'session_id':receipt['id'],'intent_id':intent['id'],'charge_id':charge['id'],
        'amount_pence':payment.amount_pence,'credits':payment.credits,'livemode':live}

class Reconcile(Strict):
    reason:str=Field(min_length=12,max_length=500)
    confirmed:bool

@router.post('/users/{user_id}/payments/{payment_id}/reconcile')
def reconcile(user_id:str,payment_id:str,data:Reconcile,u=Depends(super_admin),db=Depends(get_db)):
    if not data.confirmed or len(data.reason.strip())<12:raise HTTPException(422,'Confirm and document the reconciliation')
    payment=db.get(Payment,payment_id)
    if not payment or payment.user_id!=user_id:raise HTTPException(404,'Payment not found')
    if payment.business_id or not payment.provider_id or payment.credits<=0 or payment.amount_pence<=0:
        raise HTTPException(409,'An existing consumer Checkout purchase is required')
    provider_id=payment.provider_id
    # Release the request connection while retrieving Stripe proof. Revalidate all
    # mutable account/payment data under the same lock order as the webhook below.
    db.commit()
    receipt=provider_checkout(provider_id)
    if db.bind.dialect.name=='sqlite':db.connection().exec_driver_sql('BEGIN IMMEDIATE')
    db.refresh(u)
    if u.suspended:raise HTTPException(403,'Account unavailable')
    super_admin(u)
    person=db.scalar(select(User).where(User.id==user_id).with_for_update().execution_options(populate_existing=True))
    if not person or person.suspended or person.role in {'admin','super_admin'}:
        raise HTTPException(409,'Account requires separate operational review')
    payment=db.scalar(select(Payment).where(Payment.id==payment_id).with_for_update().execution_options(populate_existing=True))
    if not payment or payment.user_id!=user_id or payment.business_id or payment.refunded_pence or payment.dispute_status or payment.reversed_credits:
        raise HTTPException(409,'This payment has a refund, dispute or account mismatch and requires separate review')
    proof=verify_receipt(payment,receipt)
    existing=db.scalar(select(Ledger).where(Ledger.user_id==user_id,Ledger.currency=='credits',Ledger.idempotency_key=='payment:'+payment.id))
    count=db.scalar(select(func.count()).select_from(Audit).where(Audit.actor_id==u.id,Audit.action=='payment.reconciled',Audit.created_at>time.time()-86400))
    if not existing and count>=20:raise HTTPException(429,'Daily payment reconciliation limit reached')
    transaction=credit(db,user_id,payment.credits,'purchase',payment.id,'payment:'+payment.id)
    payment.intent_id=proof['intent_id'];payment.status='paid'
    from .payment_settlement import settle
    settle(db,user_id)
    if not existing:
        audit(db,u,'payment.reconciled',user_id,{'payment_id':payment.id,'transaction_id':transaction.id,
            'reason':data.reason.strip(),'proof':proof,'proof_sha256':hashlib.sha256(json.dumps(proof,sort_keys=True).encode()).hexdigest(),
            'before':transaction.previous_balance,'after':transaction.balance})
    return {'transaction':serialize(transaction),'already_recorded':existing is not None,'payment_id':payment.id}
