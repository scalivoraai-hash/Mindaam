"""Fail-fast single-replica preview launcher; durable PostgreSQL/Redis remain external."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.chdir(root)
if os.getenv("RUN_MIGRATIONS_ON_START", "true").lower() == "true":
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        check=True,
    )
children = []
shutdown_requested = False


def stop(*_):
    global shutdown_requested
    if _: shutdown_requested = True
    for child in children:
        if child.poll() is None:
            child.terminate()


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    children.append(
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ]
        )
    )
    from urllib.request import urlopen

    # First-run attributed inventory bootstrap can exceed the old 30-second window.
    # Keep readiness bounded and let Railway retain the healthy previous deployment.
    for _ in range(300):
        if children[0].poll() is not None:
            raise RuntimeError("API failed to start")
        try:
            with urlopen("http://127.0.0.1:8000/ready", timeout=1) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(0.5)
    else:
        raise RuntimeError("API readiness failed")
    children.append(
        subprocess.Popen(
            ["node", "web/apps/consumer-web/server.js"],
            env={
                **os.environ,
                "HOSTNAME": "0.0.0.0",
                "PORT": os.getenv("PORT", "3000"),
            },
        )
    )
    failures = 0
    while all(child.poll() is None for child in children):
        time.sleep(5)
        try:
            with urlopen("http://127.0.0.1:8000/api/live",timeout=3) as response:
                if response.status != 200: raise RuntimeError("Readiness failed")
            failures = 0
        except Exception:
            failures += 1
            if failures >= 3: raise RuntimeError("API liveness lost; restarting service")
finally:
    stop()
    for child in children:
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()

if not shutdown_requested:
    raise SystemExit(1)
