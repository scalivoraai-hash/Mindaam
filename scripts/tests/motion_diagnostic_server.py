"""Timing evidence for the disposable movement-settings browser fixture only."""
import gc
import json
import os
import threading
import time
from collections import deque

if os.environ.get('APP_ENV') != 'local' or not os.environ.get('DATABASE_URL', '').startswith('sqlite:////tmp/mylil-multi-speeds-'):
    raise RuntimeError('Movement diagnostics require the disposable local settings fixture')

from sqlalchemy import event
from backend.api import main
from backend.api.db import engine

app = main.app
recent = deque(maxlen=80)
local = threading.local()
gc_started = {}

def gc_timing(phase, info):
    generation = info['generation']
    if phase == 'start':
        gc_started[generation] = time.monotonic()
    else:
        elapsed = time.monotonic() - gc_started.pop(generation, time.monotonic())
        if elapsed > .02:
            record = {'kind': 'gc', 'generation': generation, 'seconds': elapsed, 'at': time.time()}
            recent.append(record)
            print('SCHEDULING_TIMING ' + json.dumps(record), flush=True)

gc.callbacks.append(gc_timing)

@event.listens_for(engine, 'before_cursor_execute')
def before_sql(conn, cursor, statement, parameters, context, executemany):
    context._qa_started = time.monotonic()

@event.listens_for(engine, 'after_cursor_execute')
def after_sql(conn, cursor, statement, parameters, context, executemany):
    elapsed = time.monotonic() - context._qa_started
    # Never record SQL text, bound values, tokens, cookies, or user identifiers.
    if elapsed > .02:
        recent.append({'kind': 'sql', 'operation': statement.split(None, 1)[0],
                       'seconds': elapsed, 'seq': getattr(local, 'seq', None), 'at': time.time()})

original = main.realtime_motion
def timed_motion(token, data):
    started, cpu = time.monotonic(), time.thread_time()
    local.seq = data.seq
    try:
        return original(token, data)
    finally:
        elapsed = time.monotonic() - started
        if elapsed > .1:
            print('MOTION_TIMING ' + json.dumps({'seq': data.seq, 'action': data.action,
                  'seconds': elapsed, 'thread_cpu_seconds': time.thread_time() - cpu,
                  'at': time.time(), 'recent': list(recent)}), flush=True)
        local.seq = None

main.realtime_motion = timed_motion


# Observe event-loop pauses outside realtime_motion as well. Code locations only:
# no frame locals, HTTP bodies, SQL parameters, tokens, or user identifiers.
import asyncio
import sys
from contextlib import asynccontextmanager

original_lifespan = app.router.lifespan_context

@asynccontextmanager
async def diagnostic_lifespan(app):
    async with original_lifespan(app):
        loop_thread = threading.get_ident()
        stopped = threading.Event()
        samples = deque(maxlen=30)
        heartbeat = [time.monotonic()]

        def sample():
            while not stopped.wait(.02):
                now = time.monotonic()
                if now - heartbeat[0] < .1:
                    continue
                frame = sys._current_frames().get(loop_thread)
                stack = []
                while frame is not None and len(stack) < 12:
                    stack.append([os.path.basename(frame.f_code.co_filename),
                                  frame.f_code.co_name, frame.f_lineno])
                    frame = frame.f_back
                samples.append({'at': time.time(), 'stack': stack})

        async def pulse():
            while True:
                await asyncio.sleep(.02)
                now = time.monotonic()
                elapsed = now - heartbeat[0]
                heartbeat[0] = now
                if elapsed > .1:
                    print('SCHEDULING_TIMING ' + json.dumps({
                        'kind': 'event_loop', 'seconds': elapsed,
                        'at': time.time(), 'samples': list(samples),
                        'recent': list(recent)}), flush=True)
                samples.clear()

        observer = threading.Thread(target=sample, daemon=True)
        observer.start()
        task = asyncio.create_task(pulse())
        try:
            yield
        finally:
            stopped.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

app.router.lifespan_context = diagnostic_lifespan
