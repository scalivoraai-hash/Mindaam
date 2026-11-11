import json
import sys
import unittest
from pathlib import Path
import sqlite3

def text(value):return value
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data_integrity import inspect_integrity, require_integrity
from common import Blocked

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        for ddl in [
            'CREATE TABLE users(id TEXT PRIMARY KEY,username TEXT)',
            'CREATE TABLE events(id TEXT PRIMARY KEY)',
            'CREATE TABLE wallet_transactions(id TEXT,user_id TEXT,currency TEXT,amount INT,kind TEXT,source TEXT,idempotency_key TEXT,previous_balance INT,balance INT,created_at REAL)']:
            self.db.execute(text(ddl))
        self.db.execute(text("INSERT INTO users VALUES ('buyer-secret-id','person'),('seller-secret-id','other')"))
        self.entry('a','buyer-secret-id','xp',50,'mission','earned',0,50,1)
        self.entry('b','buyer-secret-id','credits',20,'welcome','welcome',0,20,2)
    def tearDown(self):
        self.db.close()
    def entry(self,id,user,currency,amount,kind,key,previous,balance,created,source=''):
        self.db.execute(text('INSERT INTO wallet_transactions VALUES (:id,:user,:currency,:amount,:kind,:source,:key,:previous,:balance,:created)'),dict(id=id,user=user,currency=currency,amount=amount,kind=kind,source=source,key=key,previous=previous,balance=balance,created=created))
    def report(self):
        outer=self
        class ReadOnly:
            def execute(self,statement):
                sql=str(statement)
                outer.assertTrue(sql.lstrip().startswith('SELECT'),sql)
                if 'information_schema.tables' in sql:
                    statement=text("SELECT name AS table_name FROM sqlite_master WHERE type='table'")
                return outer.db.execute(statement)
        class Result:
            def __init__(self,cursor):self.rows=cursor.fetchall()
            def scalar_one(self):return self.rows[0][0]
            def scalars(self):return [r[0] for r in self.rows]
            def mappings(self):return [dict(r) for r in self.rows]
        return inspect_integrity(lambda sql: Result(ReadOnly().execute(sql)))
    def properties(self):
        for ddl in [
            'CREATE TABLE virtual_properties(id TEXT PRIMARY KEY,owner TEXT)',
            'CREATE TABLE virtual_property_prices(xp INT)',
            'CREATE TABLE virtual_property_offers(id TEXT)',
            'CREATE TABLE virtual_property_reversals(id TEXT)',
            'CREATE TABLE virtual_property_trades(id TEXT,property_id TEXT,buyer TEXT,seller TEXT,amount INT)']:
            self.db.execute(text(ddl))
    def test_clean_legacy_schema_and_no_identity_export(self):
        result=self.report();require_integrity(result)
        self.assertEqual(result['currencies']['xp']['balance'],50)
        self.assertFalse(result['properties']['schema_present'])
        self.assertNotIn('secret-id',json.dumps(result))
    def test_balance_chain_inconsistency_blocks(self):
        self.db.execute(text("UPDATE wallet_transactions SET balance=99 WHERE id='a'"))
        with self.assertRaises(Blocked):require_integrity(self.report())
    def test_explicit_test_credit_blocks_without_correction(self):
        self.db.execute(text("UPDATE wallet_transactions SET kind='local_browser_qa' WHERE id='a'"))
        with self.assertRaises(Blocked):require_integrity(self.report())
        self.assertEqual(self.report()['currencies']['xp']['balance'],50)
    def test_staging_account_is_reported_without_deleting_existing_users(self):
        self.db.execute(text("UPDATE users SET username='gcpqaProp123' WHERE username='person'"))
        self.assertEqual(self.report()['staging_qa_accounts'],1)
        self.assertEqual(self.report()['users'],2)
    def test_five_xp_override_requires_review(self):
        self.properties();self.db.execute(text('INSERT INTO virtual_property_prices VALUES (5)'))
        with self.assertRaises(Blocked):require_integrity(self.report())
    def test_resale_has_exact_debit_credit(self):
        self.properties()
        self.db.execute(text("INSERT INTO virtual_properties VALUES ('london:1','buyer-secret-id')"))
        self.db.execute(text("INSERT INTO virtual_property_trades VALUES ('trade','london:1','buyer-secret-id','seller-secret-id',5)"))
        self.entry('c','buyer-secret-id','xp',-5,'property_purchase','property:trade',50,45,3,'london:1')
        self.entry('d','seller-secret-id','xp',5,'property_sale','property:trade',0,5,4,'london:1')
        require_integrity(self.report())
        self.db.execute(text("DELETE FROM wallet_transactions WHERE id='d'"))
        with self.assertRaises(Blocked):require_integrity(self.report())
    def test_partial_property_schema_blocks(self):
        self.db.execute(text('CREATE TABLE virtual_properties(id TEXT)'))
        with self.assertRaises(Blocked):require_integrity(self.report())
    def test_duplicate_key_blocks(self):
        self.entry('c','buyer-secret-id','xp',1,'mission','earned',50,51,3)
        with self.assertRaises(Blocked):require_integrity(self.report())
    def test_orphan_owner_blocks(self):
        self.properties();self.db.execute(text("INSERT INTO virtual_properties VALUES ('london:1','absent')"))
        with self.assertRaises(Blocked):require_integrity(self.report())
    def test_orphan_wallet_blocks(self):
        self.entry('c','absent','xp',1,'mission','other',0,1,3)
        with self.assertRaises(Blocked):require_integrity(self.report())
