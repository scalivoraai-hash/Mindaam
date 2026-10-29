import sys,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import diagnostics
from test_deployment import FakeCloud

class Diagnostics(unittest.TestCase):
 def test_only_read_operations_and_no_approval(self):
  c=FakeCloud();calls=[]
  def get(url,token,project):
   calls.append(url);self.assertEqual(project,c.project)
   if '/services?' in url:return {'services':[]}
   return {'timeSeries':[{'metric':{'labels':{'component':'usage'}},'points':[{'value':{'doubleValue':.4}}]}]}
  with patch('diagnostics.command',return_value='test-token'),patch('diagnostics.get_json',side_effect=get),patch.object(c,'gc',return_value=[]) as gc:
   result=diagnostics.collect(c)
   self.assertEqual(len(result['metrics']),8);self.assertFalse(result['release_approval'])
   self.assertEqual(result['memory_gate_threshold'],.9);self.assertEqual(result['errors'],{})
   self.assertEqual(gc.call_args.args[:2],('logging','read'))
   self.assertTrue(all('/timeSeries?' in u or '/services?' in u for u in calls))
   self.assertNotIn('test-token',str(result))
 def test_denied_reads_are_not_healthy_results(self):
  c=FakeCloud()
  with patch('diagnostics.command',return_value='test-token'),patch('diagnostics.get_json',side_effect=HTTPError('https://example',403,'denied',{},None)),patch.object(c,'gc',side_effect=RuntimeError('sensitive diagnostic')):
   result=diagnostics.collect(c)
   self.assertEqual(result['metrics'],{});self.assertEqual(result['errors']['memory/components'],'HTTP 403')
   self.assertIn('memory_error_logs',result['errors']);self.assertNotIn('sensitive diagnostic',str(result))
   self.assertEqual(result['public_prices']['errors']['catalog'],'HTTP 403')
 def test_catalog_filters_region_and_commitments(self):
  c=FakeCloud();base={'category':{'usageType':'OnDemand'},'description':'test-only rate','serviceRegions':[c.region]}
  responses=[{'services':[{'name':'services/test','displayName':'Cloud SQL'}]}, {'skus':[dict(base,skuId='keep'),dict(base,skuId='wrong-region',serviceRegions=['us-central1']),dict(base,skuId='commitment',category={'usageType':'Commit1Yr'})]}]
  with patch('diagnostics.get_json',side_effect=responses):
   result=diagnostics.prices(c,'test-token');self.assertEqual([s['skuId'] for s in result['skus']],['keep'])
