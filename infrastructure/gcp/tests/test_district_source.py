import os, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Blocked
from district_source import verify_source

class DistrictSource(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.previous=os.getcwd()
        os.chdir(self.temp.name)
        self.git("init","-q")
        self.git("config","user.email","qa@example.test")
        self.git("config","user.name","QA")
        self.write("backend/app.py","original")
        self.base=self.commit()
    def tearDown(self):
        os.chdir(self.previous)
        self.temp.cleanup()
    def git(self,*args):
        return subprocess.check_output(["git",*args],text=True,stderr=subprocess.DEVNULL).strip()
    def write(self,path,body):
        p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
    def commit(self):
        self.git("add",".");self.git("commit","-qm","fixture")
        return self.git("rev-parse","HEAD")
    def test_unchanged_image_accepts_new_harness_and_records_both_shas(self):
        self.write("infrastructure/gcp/district-browser.cjs","reviewed driver")
        head=self.commit()
        self.assertEqual(verify_source(self.base,head),{"application_sha":self.base,"harness_sha":head})
    def test_application_drift_is_rejected(self):
        self.write("backend/app.py","changed");head=self.commit()
        with self.assertRaises(Blocked):verify_source(self.base,head)
    def test_application_test_changes_are_rejected(self):
        self.write("scripts/tests/movement.cjs","changed assertions");head=self.commit()
        with self.assertRaises(Blocked):verify_source(self.base,head)
    def test_reverse_history_and_invalid_refs_are_rejected(self):
        self.write("infrastructure/gcp/diagnostics.py","diagnostics");head=self.commit()
        with self.assertRaises(Blocked):verify_source(head,self.base)
        with self.assertRaises(Blocked):verify_source("main",head)
