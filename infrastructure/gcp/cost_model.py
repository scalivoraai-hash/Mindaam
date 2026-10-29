"""Conservative, explicit public-beta usage scenarios from current regional SKU evidence."""
import datetime,math
from common import Blocked

RATES={
 'sql':('DCEF-DAD9-FBDD','h'), 'sql_disk':('A025-9006-CE7C','GiBy.mo'),
 'backup':('F2C3-43B1-30A7','GiBy.mo'), 'vm_cpu':('0F2A-2FA8-3F6A','h'),
 'vm_ram':('5D70-7762-2DE7','GiBy.h'), 'vm_disk':('BF1A-6647-009D','GiBy.mo'),
 'ip':('C054-7F72-A02E','h'), 'run_cpu':('085C-A237-027A','s'),
 'run_ram':('600C-3782-6708','GiBy.s'), 'requests':('2DA5-55D3-E679','count'),
 'egress':('1ADA-20B0-CAED','GiBy'), 'artifacts':('8502-299A-ABAF','GiBy.mo'),
 'objects':('BB55-3E5A-405C','GiBy.mo'), 'secrets':('7756-ADEF-84F4','mo'),
 'secret_access':('EBA7-264F-2D2C','count'), 'logs':('143F-A1B0-E0BE','GiBy')}


def estimate(value):
 inv=value['inventory'];prices=value['database_diagnostics']['public_prices']
 if prices.get('errors') or prices.get('region')!='europe-west2':raise Blocked('Complete London pricing evidence is required')
 if inv['sql']['settings']['tier']!='db-f1-micro' or not inv['vm']['machineType'].endswith('/e2-small'):
  raise Blocked('Cost model must be recalculated for changed database/VM size')
 if inv['production_limits']['cpu']!='1' or inv['production_limits']['memory']!='1Gi' or sum(int(d['diskSizeGb']) for d in inv['vm']['disks'])!=20:
  raise Blocked('Cost model must be recalculated for changed Run/disk configuration')
 skus={s['skuId']:s for s in prices['skus']}; rates={}
 for name,(sku,unit) in RATES.items():
  expression=skus[sku]['pricingInfo'][-1]['pricingExpression']
  if expression['usageUnit']!=unit:raise Blocked('Pricing unit changed: '+sku)
  positive=[]
  for tier in expression['tieredRates']:
   p=tier['unitPrice']; rate=int(p['units'])+p.get('nanos',0)/1e9
   if p['currencyCode']!='USD' or not math.isfinite(rate) or rate<0:raise Blocked('Invalid price: '+sku)
   if rate>0:positive.append(rate)
  if not positive:raise Blocked('Paid unit rate missing: '+sku)
  rates[name]=max(positive) # No free-tier, credit or negotiated-discount assumptions.
 costs={}
 for scenario,hours,requests,egress,logs,userhours,publisher,receiver in [
  ('idle',2,10000,1,1,0,0,0),('light',200,1000000,100,10,500,20,80)]:
  assumptions={'month_hours':730,'billed_cloud_run_instance_hours_total_staging_and_production':hours,
   'connected_user_hours':userhours,'media_publisher_hours':publisher,'media_receiver_hours':receiver,
   'internet_egress_gib':egress,'api_requests':requests,'backup_gib_allowance':70,
   'artifact_gib_allowance':20,'release_object_gib_allowance':10,'secret_versions_allowance':36,
   'secret_access_operations':50000,'logging_gib':logs,'other_contingency_usd':5,
   'free_tier_and_credits_applied':False,'tax_included':False,
   'note':'Usage assumptions, not measured future traffic or a bill ceiling. UK/Western Europe egress. VM includes Redis. Backup/WAL, storage and request variation require billing monitoring.'}
  amounts={'cloud_run':hours*3600*(rates['run_cpu']+rates['run_ram'])+requests*rates['requests'],
   'compute_livekit':730*(.5*rates['vm_cpu']+2*rates['vm_ram']),
   'postgresql':730*rates['sql']+int(inv['sql']['settings']['dataDiskSizeGb'])*rates['sql_disk']+70*rates['backup'],
   'redis':0,'storage':20*rates['vm_disk']+20*rates['artifacts']+10*rates['objects'],
   'network':730*rates['ip']+egress*rates['egress'],'logging':logs*rates['logs'],
   'other':36*rates['secrets']+50000*rates['secret_access']+5}
  costs[scenario]={'assumptions':assumptions,'pricing_sources':['https://cloudbilling.googleapis.com/v1/services','https://cloud.google.com/compute/all-pricing','https://cloud.google.com/run/pricing'],
                   'usd':{k:round(v,4) for k,v in amounts.items()}}
 return {'costs':costs,'pricing_date':datetime.date.today().isoformat(),'unit_rates_usd':rates,
         'price_skus':{k:v[0] for k,v in RATES.items()},'cost_approval_status':'PENDING OWNER APPROVAL'}
