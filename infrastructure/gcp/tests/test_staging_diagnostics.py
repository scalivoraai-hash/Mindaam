import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from staging_diagnostics import summarize
class StagingDiagnostics(unittest.TestCase):
 def test_private_log_values_never_exported(self):
  rows=[{'timestamp':'now','severity':'ERROR','textPayload':'private@example.test password=secret sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 5 reached, connection timed out, timeout 5.00 [SQL: private account query]'}]
  result=summarize(rows)
  self.assertEqual(result[0]['signals']['pool_exhaustion'],['QueuePool limit of size 5 overflow 5 reached, connection timed out, timeout 5.00'])
  self.assertNotIn('secret',str(result));self.assertNotIn('private',str(result));self.assertNotIn('SQL:',str(result))

 def test_only_code_locations_and_statement_kind_exported(self):
  row={'textPayload':'File "/app/backend/api/talk.py", line 82, in member\n[SQL: SELECT media_sessions.id FROM media_sessions WHERE token=secret]'}
  signals=summarize([row])[0]['signals']
  self.assertEqual(signals['backend_frames'],[{'file':'talk.py','line':82,'function':'member'}])
  self.assertEqual(signals['statement_kinds'],[{'operation':'SELECT','relation':'media_sessions'}])
  self.assertNotIn('secret',str(signals))
