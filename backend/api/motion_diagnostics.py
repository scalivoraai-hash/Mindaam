"""Bounded operational diagnostics for blocked virtual movement, never device GPS."""
import gc,json,logging,math,os,time
from collections import OrderedDict,deque
from contextlib import contextmanager
from threading import Lock
_pending=OrderedDict();_lock=Lock();logger=logging.getLogger('pulseworld.motion')
_last_timing=0.0
DETAILS={'connection_ms','sql_ms','sql_max_ms','sql_count','thread_cpu_ms','gc_overlap_ms'}
_gc_events=deque(maxlen=32);_gc_start={}
def _gc_timing(phase,info):
 generation=info['generation'];now=time.monotonic()
 if phase=='start':_gc_start[generation]=now
 else:
  started=_gc_start.pop(generation,now)
  if now-started>=.02:_gc_events.append((started,now))
if os.getenv('APP_ENV')=='staging':gc.callbacks.append(_gc_timing)

@contextmanager
def transaction_probe(db):
 """Measure only this movement connection; never retain SQL or parameters."""
 values={}
 if os.getenv('APP_ENV')!='staging':
  yield values
  return
 from sqlalchemy import event
 started=time.monotonic();cpu=time.thread_time()
 conn=db.connection()
 values.update(connection_ms=1000*(time.monotonic()-started),sql_ms=0.,sql_max_ms=0.,sql_count=0)
 def before(conn,cursor,statement,parameters,context,many):
  context._motion_started=time.monotonic()
 def after(conn,cursor,statement,parameters,context,many):
  elapsed=1000*(time.monotonic()-context._motion_started)
  values['sql_ms']+=elapsed;values['sql_max_ms']=max(values['sql_max_ms'],elapsed);values['sql_count']+=1
 event.listen(conn,'before_cursor_execute',before)
 event.listen(conn,'after_cursor_execute',after)
 try:yield values
 finally:
  event.remove(conn,'before_cursor_execute',before)
  event.remove(conn,'after_cursor_execute',after)
  ended=time.monotonic()
  values['thread_cpu_ms']=1000*(time.thread_time()-cpu)
  values['gc_overlap_ms']=1000*sum(max(0,min(ended,b)-max(started,a)) for a,b in list(_gc_events))

def timing(started, received, phases, details=None):
 """Staging-only aggregate phases; no identity, coordinates, SQL or tokens."""
 global _last_timing
 if os.getenv('APP_ENV','local')!='staging':return
 ended=time.monotonic()
 if ended-started<.35:return
 with _lock:
  if ended-_last_timing<10:return
  _last_timing=ended
 values={};previous=started
 for name,at in [*phases,('commit_and_publish',ended)]:
  values[name+'_ms']=round(1000*(at-previous),1);previous=at
 values['queue_ms']=round(1000*max(0,started-received),1) if received is not None else None
 values.update({k:round(v,1) for k,v in (details or {}).items() if k in DETAILS and type(v) in (int,float) and math.isfinite(v) and v>=0})
 logger.warning('movement_transaction_timing %s',json.dumps(values))

def observe(user_id,city,zone,mode,x,z,attempted,blocked):
 now=time.monotonic();threshold=max(1.5,min(10,float(os.getenv('WORLD_STALL_SECONDS','2.5'))))
 with _lock:
  if not attempted or not blocked:
   _pending.pop(user_id,None);return
  since,last=_pending.pop(user_id,(now,0))
  _pending[user_id]=(since,last)
  while len(_pending)>4096:_pending.popitem(last=False)
  if now-since<threshold or last and now-last<60:return
  _pending[user_id]=(since,now)
 details={'event':'vehicle_stuck' if mode not in ['walk','run'] else 'player_stuck','user_id':user_id,'destination':city,'zone':zone,'mode':mode,'x':round(x,2),'z':round(z,2),'collider':'mapped_path_boundary_or_building','device':'unknown','performance':'unknown'}
 logger.warning('movement_input_without_displacement %s',json.dumps(details),extra={'motion':details})
