"""Aggregate release audit. Caller must establish a read-only transaction."""
import hashlib
import json
from collections import defaultdict

QA_KINDS = {'test', 'test_credit', 'seed', 'local_browser_qa'}
PROPERTY_TABLES = {'virtual_properties', 'virtual_property_prices', 'virtual_property_trades',
                   'virtual_property_offers', 'virtual_property_reversals'}

def inspect_integrity(execute):
    scalar=lambda sql: int(execute(sql).scalar_one())
    fingerprint=lambda sql: hashlib.sha256(json.dumps([dict(r) for r in execute(sql).mappings()],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    tables=set(execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'").scalars())
    entries=list(execute("SELECT id,user_id,currency,amount,kind,source,idempotency_key,previous_balance,balance,created_at FROM wallet_transactions ORDER BY user_id,currency,created_at,id").mappings())
    grouped=defaultdict(list)
    for row in entries:grouped[(row['user_id'],row['currency'])].append(row)
    currencies={}
    for currency in ('xp','credits'):
        accounts=[rows for (_,kind),rows in grouped.items() if kind==currency]
        inconsistent=negative=0
        for rows in accounts:
            running=0;valid=True
            for row in rows:
                valid &= row['previous_balance']==running and row['balance']==running+row['amount']
                running+=row['amount']
            inconsistent+=not valid;negative+=running<0
        rows=[r for r in entries if r['currency']==currency]
        currencies[currency]={'accounts':len(accounts),'entries':len(rows),
            'balance':sum(r['amount'] for r in rows),'inconsistent_accounts':inconsistent,
            'negative_accounts':negative,'qa_kind_entries':sum(r['kind'] in QA_KINDS for r in rows),
            'ledger_sha256':hashlib.sha256(json.dumps([dict(r) for r in rows],sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    result={'read_only':True,'users':scalar('SELECT count(*) FROM users'),
        'events':scalar('SELECT count(*) FROM events'),'currencies':currencies,
        'user_ids_sha256':fingerprint('SELECT id FROM users ORDER BY id'),
        'event_ids_sha256':fingerprint('SELECT id FROM events ORDER BY id'),
        'staging_qa_accounts':scalar("SELECT count(*) FROM users WHERE lower(username) LIKE 'gcpqa%'"),
        'orphan_wallet_entries':scalar('SELECT count(*) FROM wallet_transactions w LEFT JOIN users u ON u.id=w.user_id WHERE u.id IS NULL'),
        'duplicate_wallet_keys':scalar('SELECT count(*) FROM (SELECT user_id,currency,idempotency_key FROM wallet_transactions GROUP BY user_id,currency,idempotency_key HAVING count(*)>1) duplicates')}
    present=PROPERTY_TABLES & tables
    properties={'schema_present':present==PROPERTY_TABLES,'partial_schema':bool(present) and present!=PROPERTY_TABLES}
    if properties['schema_present']:
        properties.update(
            registered=scalar('SELECT count(*) FROM virtual_properties'),
            owned=scalar('SELECT count(*) FROM virtual_properties WHERE owner IS NOT NULL'),
            ownership_sha256=fingerprint('SELECT id,owner FROM virtual_properties WHERE owner IS NOT NULL ORDER BY id'),
            trades=scalar('SELECT count(*) FROM virtual_property_trades'),
            orphan_owners=scalar('SELECT count(*) FROM virtual_properties p LEFT JOIN users u ON u.id=p.owner WHERE p.owner IS NOT NULL AND u.id IS NULL'),
            five_xp_overrides=scalar('SELECT count(*) FROM virtual_property_prices WHERE xp=5'),
            malformed_trade_ledger=scalar("""SELECT count(*) FROM virtual_property_trades t WHERE
                (SELECT count(*) FROM wallet_transactions w WHERE w.currency='xp' AND w.kind='property_purchase'
                 AND w.user_id=t.buyer AND w.amount=-t.amount AND w.source=t.property_id
                 AND w.idempotency_key='property:' || t.id)<>1 OR
                (t.seller IS NOT NULL AND (SELECT count(*) FROM wallet_transactions w WHERE w.currency='xp'
                 AND w.kind='property_sale' AND w.user_id=t.seller AND w.amount=t.amount
                 AND w.source=t.property_id AND w.idempotency_key='property:' || t.id)<>1)"""),
            orphan_trade_entries=scalar("""SELECT count(*) FROM wallet_transactions w WHERE w.kind IN ('property_purchase','property_sale')
                AND NOT EXISTS (SELECT 1 FROM virtual_property_trades t WHERE w.idempotency_key='property:' || t.id)"""))
    else:
        properties['trade_entries_without_schema']=sum(r['kind'] in {'property_purchase','property_sale'} for r in entries)
    result['properties']=properties
    return result

def require_integrity(result):
    from common import Blocked
    if result.get('read_only') is not True:raise Blocked('Read-only integrity evidence missing')
    for currency in ('xp','credits'):
        value=result.get('currencies',{}).get(currency,{})
        if any(value.get(k)!=0 for k in ('inconsistent_accounts','negative_accounts','qa_kind_entries')):
            raise Blocked('Wallet integrity review required: '+currency)
    if any(result.get(k)!=0 for k in ('orphan_wallet_entries','duplicate_wallet_keys')):
        raise Blocked('Account or wallet integrity review required')
    p=result.get('properties',{})
    if p.get('partial_schema') is not False:raise Blocked('Partial property schema')
    keys=('orphan_owners','five_xp_overrides','malformed_trade_ledger','orphan_trade_entries') if p.get('schema_present') else ('trade_entries_without_schema',)
    if any(p.get(k)!=0 for k in keys):raise Blocked('Property integrity review required; no automatic corrections')
