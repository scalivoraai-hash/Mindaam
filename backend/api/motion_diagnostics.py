"""Bounded operational diagnostics for blocked virtual movement, never device GPS."""
import json,logging,os,time
from collections import OrderedDict
from threading import Lock
_pending=OrderedDict();_lock=Lock();logger=logging.getLogger('pulseworld.motion')
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
