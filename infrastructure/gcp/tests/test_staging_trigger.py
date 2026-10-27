import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Blocked
from staging_trigger import release_from_event

class StagingTrigger(unittest.TestCase):
    def test_trusted_successful_push_only(self):
        repo='scalivoraai-hash/Mindaam'
        event={'workflow_run':{'name':'Validation','event':'push','head_branch':'main','conclusion':'success','head_repository':{'full_name':repo},'head_sha':'a'*40}}
        self.assertEqual(release_from_event(event,repo),'a'*40)
        for key,value in [('event','pull_request'),('head_branch','feature'),('conclusion','skipped'),('conclusion','failure'),('name','Other workflow'),('head_sha','not-a-sha'),('head_repository',{'full_name':'fork/Mindaam'})]:
            bad=copy.deepcopy(event);bad['workflow_run'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(Blocked):release_from_event(bad,repo)
        with self.assertRaises(Blocked):release_from_event(event,'someone/else')
