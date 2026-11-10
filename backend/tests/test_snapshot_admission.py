"""Snapshot waiters must not hold a database connection or return stale state."""
import asyncio
from threading import Event
from sqlalchemy import create_engine,text
from backend.api import main

def test_snapshot_waiters_leave_pool_capacity_for_movement(tmp_path):
    engine=create_engine('sqlite:///'+str(tmp_path/'admission.db'),pool_size=2,max_overflow=0,pool_timeout=.1,
                         connect_args={'check_same_thread':False})
    started,release=Event(),Event();seen=[];current={'revision':1}
    def build():
        with engine.connect() as db:
            db.execute(text('SELECT 1'))
            seen.append(current['revision']);started.set()
            assert release.wait(2)
            return current['revision']
    async def run():
        main.app.state.realtime_snapshot_gate=asyncio.Semaphore(1)
        tasks=[asyncio.create_task(main.sample_realtime_state(build)) for _ in range(3)]
        try:
            assert await asyncio.to_thread(started.wait,1)
            await asyncio.sleep(.05)
            # A real second checkout must remain available while snapshots queue.
            with engine.connect() as movement:
                assert movement.execute(text('SELECT 1')).scalar()==1
            assert seen==[1]
            current['revision']=2;release.set()
            assert await asyncio.gather(*tasks)==[2,2,2]
            assert seen==[1,2,2]
        finally:
            release.set()
            await asyncio.gather(*tasks,return_exceptions=True)
    try:asyncio.run(run())
    finally:engine.dispose()

def test_cancelled_waiter_and_failed_reader_release_admission():
    async def run():
        gate=main.app.state.realtime_snapshot_gate=asyncio.Semaphore(1)
        await gate.acquire()
        waiter=asyncio.create_task(main.sample_realtime_state(lambda:None))
        await asyncio.sleep(0);waiter.cancel()
        await asyncio.gather(waiter,return_exceptions=True);gate.release()
        def fail():raise ValueError('sample failed')
        try:await main.sample_realtime_state(fail)
        except ValueError:pass
        else:raise AssertionError('Reader error was hidden')
        assert await main.sample_realtime_state(lambda:'fresh')=='fresh'
    asyncio.run(run())

def test_disconnect_keeps_admission_until_database_worker_finishes():
    started,release,second=Event(),Event(),Event()
    def build():
        started.set();assert release.wait(2)
    async def run():
        main.app.state.realtime_snapshot_gate=asyncio.Semaphore(1)
        first=asyncio.create_task(main.sample_realtime_state(build))
        assert await asyncio.to_thread(started.wait,1)
        first.cancel()
        next_reader=asyncio.create_task(main.sample_realtime_state(second.set))
        try:
            await asyncio.sleep(.05)
            assert not second.is_set()
        finally:
            release.set()
            await asyncio.gather(first,next_reader,return_exceptions=True)
        assert second.is_set() and first.cancelled()
    asyncio.run(run())
