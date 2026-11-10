"""HTTP fallback cannot consume a connection while a socket owns admission."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from backend.tests.test_core import system,register,onboard
from backend.api import main
from backend.api.db import get_db

def test_http_snapshot_waits_before_opening_auth_session(system):
    client,sessions=system
    headers,user=register(client,'http_admission');onboard(client,headers)
    original=main.app.dependency_overrides[get_db]
    opened=Event()
    def dependency():
        opened.set()
        yield from original()
    main.app.dependency_overrides[get_db]=dependency
    gate=main.app.state.realtime_snapshot_gate
    client.portal.call(gate.acquire)
    with ThreadPoolExecutor(max_workers=1) as pool:
        result=pool.submit(client.get,'/api/world/london',headers=headers)
        try:
            assert not opened.wait(.1)
            assert not result.done()
        finally:client.portal.call(gate.release)
        response=result.result(timeout=5)
    assert response.status_code==200,response.text
    assert opened.is_set()
    assert client.get('/api/world/london').status_code==401

def test_cancelled_waiting_http_read_does_not_take_admission():
    import asyncio
    from types import SimpleNamespace
    from backend.api.world import snapshot_admission
    async def run():
        gate=asyncio.Semaphore(1)
        request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(realtime_snapshot_gate=gate)))
        await gate.acquire()
        waiter=snapshot_admission(request)
        task=asyncio.create_task(anext(waiter));await asyncio.sleep(0)
        task.cancel();await asyncio.gather(task,return_exceptions=True)
        gate.release()
        async with gate:assert gate.locked()
        assert not gate.locked()
    asyncio.run(run())
