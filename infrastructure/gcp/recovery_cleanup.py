"""Recover only the temporary instance from the recorded interrupted drill."""
import json,time
from pathlib import Path
from common import Blocked
from recovery import guard,SHA
NAME='mindaam-recovery-40800112127-1'
RUN='40800112127'
def run(c,sha):
 if c.project!='mindaam' or sha!=SHA:raise Blocked('Exact recovery project/release required')
 result={'sha':sha,'target':NAME,'cleanup':False,'operations':[]}
 Path('gcp-evidence').mkdir(exist_ok=True)
 try:
  instances=c.gc('sql','instances','list')
  current=next((x for x in instances if x['name']==NAME),None)
  if current is None:result['cleanup']=True;return
  guard(current,NAME,RUN)
  operations=c.gc('sql','operations','list','--instance='+NAME,'--limit=20')
  result['operations']=[{k:x.get(k) for k in ('name','operationType','status','startTime','endTime','error')} for x in operations]
  print(json.dumps(result['operations']))
  for op in operations:
   if op['status']!='DONE':c.gc('sql','operations','wait',op['name'],'--timeout=3600')
  guard(c.gc('sql','instances','describe',NAME),NAME,RUN)
  jobs=c.gc('run','jobs','list','--region='+c.region)
  if any(x.get('metadata',{}).get('name')==NAME for x in jobs):c.gc('run','jobs','delete',NAME,'--region='+c.region)
  c.gc('sql','instances','delete',NAME)
  result['cleanup']=not any(x['name']==NAME for x in c.gc('sql','instances','list'))
 finally:
  result['checked_at']=int(time.time())
  Path('gcp-evidence/recovery-cleanup.json').write_text(json.dumps(result,indent=2))
  c.put_json(f'releases/{sha}/recovery-cleanup.json',result)
 if not result['cleanup']:raise Blocked('Recovery instance removal unverified')
