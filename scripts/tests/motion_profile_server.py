"""Local browser-test timing; never a production entry point or private payload log."""
import functools
import asyncio
from contextlib import asynccontextmanager
import json
import os
import threading
import time

if os.environ.get('APP_ENV') != 'local' or not os.environ.get('DATABASE_URL', '').startswith('sqlite:////tmp/mylil-multi-'):
    raise RuntimeError('Motion profiling requires a disposable local QA database')

from sqlalchemy import event
from backend.api import main, world, mobility
from backend.api.db import engine

context = threading.local()
original_pool = main.run_in_threadpool

async def traced_pool(fn, *args, **kwargs):
    queued = time.perf_counter()
    def execute():
        delay = (time.perf_counter() - queued) * 1000
        if delay > 80:
            print('QA_POOL_WAIT ' + json.dumps({'function': fn.__name__, 'ms': round(delay, 2)}), flush=True)
        return fn(*args, **kwargs)
    return await original_pool(execute)

main.run_in_threadpool = traced_pool
original_lifespan = main.app.router.lifespan_context

async def loop_watch():
    while True:
        started = time.perf_counter()
        await asyncio.sleep(.05)
        delay = (time.perf_counter() - started - .05) * 1000
        if delay > 80:
            print('QA_LOOP_DELAY ' + json.dumps({'ms': round(delay, 2)}), flush=True)

@asynccontextmanager
async def traced_lifespan(app):
    async with original_lifespan(app):
        watcher = asyncio.create_task(loop_watch())
        try:
            yield
        finally:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)

main.app.router.lifespan_context = traced_lifespan

@event.listens_for(engine, 'before_cursor_execute')
def sql_start(conn, cursor, statement, parameters, ctx, many):
    ctx.qa_start = time.perf_counter()

@event.listens_for(engine, 'after_cursor_execute')
def sql_end(conn, cursor, statement, parameters, ctx, many):
    row = getattr(context, 'row', None)
    if row is not None:
        elapsed = (time.perf_counter() - ctx.qa_start) * 1000
        row['sql_count'] += 1
        row['sql_ms'] += elapsed
        if elapsed > 20:
            # Statement class only: never bound values, tokens or user content.
            row['slow_sql'].append({'operation': statement.split()[0], 'ms': round(elapsed, 2)})

def timed(module, name):
    original = getattr(module, name)
    @functools.wraps(original)
    def call(*args, **kwargs):
        previous = getattr(context, 'row', None)
        row = {'function': module.__name__ + '.' + name, 'sql_count': 0, 'sql_ms': 0, 'slow_sql': []}
        context.row = row
        started = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            row['ms'] = round((time.perf_counter() - started) * 1000, 2)
            row['sql_ms'] = round(row['sql_ms'], 2)
            context.row = previous
            if previous is not None:
                previous.setdefault('calls', []).append(row)
            if row['ms'] > 80:
                print('QA_SERVER_TIMING ' + json.dumps(row), flush=True)
    setattr(module, name, call)

for module, name in [(main,'realtime_state'),(main,'realtime_motion'),(main,'maintenance'),(world,'snapshot'),(world,'move'),(mobility,'drive')]:
    timed(module, name)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(main.app, host='127.0.0.1', port=8000)
