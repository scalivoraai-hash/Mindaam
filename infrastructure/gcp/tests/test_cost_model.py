import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cost_model import RATES,estimate
from common import Blocked
class CostModel(unittest.TestCase):
 def fixture(self):
  return {'inventory':{'sql':{'settings':{'tier':'db-f1-micro','dataDiskSizeGb':'10'}},'vm':{'machineType':'test/e2-small','disks':[{'diskSizeGb':'20'}]},'production_limits':{'cpu':'1','memory':'1Gi'}},'database_diagnostics':{'public_prices':{'region':'europe-west2','errors':{},'skus':[{'skuId':sku,'pricingInfo':[{'pricingExpression':{'usageUnit':unit,'tieredRates':[{'unitPrice':{'currencyCode':'USD','units':'0','nanos':1}}]}}]} for sku,unit in RATES.values()]}}}
 def test_explicit_estimates_never_approve_or_apply_free_credits(self):
  value=self.fixture();before=copy.deepcopy(value);r=estimate(value)
  self.assertEqual(value,before);self.assertEqual(r['cost_approval_status'],'PENDING OWNER APPROVAL');self.assertNotIn('owner_approved',r)
  self.assertEqual(r['costs']['light']['assumptions']['billed_cloud_run_instance_hours_total_staging_and_production'],200)
  self.assertFalse(r['costs']['light']['assumptions']['free_tier_and_credits_applied'])
 def test_changed_config_region_or_units_block(self):
  for mutate in [lambda x:x['inventory']['sql']['settings'].update(tier='db-g1-small'),lambda x:x['database_diagnostics']['public_prices'].update(region='us-central1'),lambda x:x['database_diagnostics']['public_prices']['skus'][0]['pricingInfo'][0]['pricingExpression'].update(usageUnit='month')]:
   v=self.fixture();mutate(v)
   with self.assertRaises(Blocked):estimate(v)
