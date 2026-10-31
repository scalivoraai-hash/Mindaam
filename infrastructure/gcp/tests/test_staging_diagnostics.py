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

 def test_production_requests_redact_private_path_query_and_headers(self):
  from production_diagnostics import request_summary
  rows=[{'httpRequest':{'requestUrl':'https://mindaam.com/api/auth/login?password=secret','status':503,'remoteIp':'private'}},
        {'httpRequest':{'requestUrl':'https://mindaam.com/api/users/private@example.test','status':500}}]
  value=request_summary(rows)
  self.assertEqual(value[0]['path'],'/api/auth/login')
  self.assertEqual(value[1]['path'],'[other route]')
  self.assertNotIn('secret',str(value));self.assertNotIn('private',str(value))

 def test_runtime_error_categories_keep_connection_details_private(self):
  value=summarize([{'textPayload':'connection to server at private-host failed: Connection refused; password authentication failed for private-user; no available instance; database system is starting up'}])
  self.assertEqual(set(value[0]['signals']),{'connection_refused','auth_failed','no_available_instance','database_starting'})
  self.assertNotIn('private',str(value))

 def test_orm_cleanup_exception_and_http_status_are_redacted(self):
  row={'textPayload':"sqlalchemy.orm.exc.ObjectDeletedError: private@example.test secret row",'httpRequest':{'status':499,'requestUrl':'https://private/?token=secret'}}
  signals=summarize([row])[0]['signals']
  self.assertEqual(signals,{'exception_type':['sqlalchemy.orm.exc.ObjectDeletedError'],'http_status':499})
  self.assertNotIn('private',str(signals));self.assertNotIn('secret',str(signals))

 def test_payment_gate_routes_hide_ids_and_queries(self):
  row={'httpRequest':{'status':503,'requestUrl':'https://mindaam.com/api/events/private-event/venue/booking?token=secret'}}
  signals=summarize([row])[0]['signals']
  self.assertEqual(signals,{'http_status':503,'request_route':'/api/events/[id]/venue/booking'})
  self.assertNotIn('secret',str(signals));self.assertNotIn('private-event',str(signals))
