import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evidence import sql_memory_samples
from common import Blocked
class SQLMemory(unittest.TestCase):
 def fixture(self,usage=12):
  return {'series':{'cloudsql.googleapis.com/database/memory/components':{'timeSeries':[{'metric':{'labels':{'component':k}},'points':[{'interval':{'endTime':f'2026-10-29T00:0{i}:00Z'},'value':{'doubleValue':v}} for i in range(5)]} for k,v in [('Usage',usage),('Cache',5),('Free',95-usage)]]}}}
 def test_percent_normalization_retains_ninety_percent_boundary(self):
  self.assertEqual(sql_memory_samples(self.fixture()),[.12]*5)
  self.assertTrue(all(v>.9 for v in sql_memory_samples(self.fixture(94))))
 def test_missing_invalid_or_nonreconciling_data_blocks(self):
  with self.assertRaises(Blocked):sql_memory_samples({})
  for value in [float('nan'),-1,101,True,.12]:
   data=self.fixture();data['series']['cloudsql.googleapis.com/database/memory/components']['timeSeries'][0]['points'][0]['value']['doubleValue']=value
   with self.assertRaises(Blocked):sql_memory_samples(data)
 def test_paginated_series_use_latest_timestamps(self):
  data=self.fixture();series=data['series']['cloudsql.googleapis.com/database/memory/components']['timeSeries']
  for row in copy.deepcopy(series):
   for p in row['points']:p['interval']['endTime']=p['interval']['endTime'].replace('2026-10-29','2026-10-28')
   series.append(row)
  self.assertEqual(sql_memory_samples(data),[.12]*5)
