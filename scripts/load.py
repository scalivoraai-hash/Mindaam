"""Bounded authenticated HTTP load check; no fabricated user/scale claim.
PULSE_LOAD_URL=http://127.0.0.1:8000 PULSE_LOAD_TOKEN=... python scripts/load.py
"""
import asyncio,json,os,time,statistics
import httpx
async def main():
    token=os.environ['PULSE_LOAD_TOKEN'];url=os.getenv('PULSE_LOAD_URL','http://127.0.0.1:8000')
    semaphore=asyncio.Semaphore(10);results=[]
    async with httpx.AsyncClient(base_url=url,headers={'Authorization':'Bearer '+token},timeout=15) as client:
        async def request():
            async with semaphore:
                started=time.perf_counter()
                try:r=await client.get('/api/wallet');status=r.status_code
                except httpx.HTTPError:status=0
                results.append((time.perf_counter()-started,status))
        await asyncio.gather(*(request() for _ in range(100)))
    latency=sorted(r[0]*1000 for r in results)
    print(json.dumps({'requests':len(results),'concurrency':10,'successes':sum(s==200 for _,s in results),'latency_ms':{'median':round(statistics.median(latency),2),'p95':round(latency[94],2)},'scope':'Single account wallet reads. Not a multiplayer scalability certification.'},indent=2))
if __name__=='__main__':asyncio.run(main())
