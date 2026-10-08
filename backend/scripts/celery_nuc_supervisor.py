#!/usr/bin/env python3
"""Run the NUC scrape worker and the maintenance/beat worker in one container.

Zone scrapes sit on the ``scrape`` queue. Digest, expiry, and currency tasks
sit on ``maintenance`` so a multi-hour scrape cannot block them. This process
is PID 1: it drops to ``appuser`` for the workers and forwards stop signals.

Compose starts this file by absolute path
(``python /app/scripts/celery_nuc_supervisor.py``). That puts ``scripts/`` on
``sys.path[0]``, not the backend root, so ``import app`` fails unless the
parent of ``scripts/`` is inserted first. ``PYTHONPATH=/app`` in
``docker-compose.nuc.yml`` is a second copy of the same fix.
"""

from __future__ import annotations

import os
import pwd
import signal
import subprocess
import sys
import time
from pathlib import Path

# Absolute-path invocation sets sys.path[0] to this file's directory.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.scrapers.zones import scrape_concurrency  # noqa: E402

APP_USER = "appuser"
_CELERY = [
    "celery",
    "-A",
    "app.workers.celery_app.celery_app",
    "worker",
]
_MAINTENANCE = [
    *_CELERY,
    "--beat",
    "--loglevel=info",
    "-Q",
    "maintenance",
    "--concurrency=1",
    "-n",
    "maintenance@%h",
    "-s",
    "/app/data/celerybeat-schedule",
]


def _scrape_command() -> list[str]:
    # ``celery`` is the old default queue. Keep draining it so a restart does not
    # strand zone tasks Beat already published before the queue split.
    # Concurrency is SCRAPE_CONCURRENCY (default 6). Maintenance stays at 1.
    slots = scrape_concurrency()
    return [
        *_CELERY,
        "--loglevel=info",
        "-Q",
        "scrape,celery",
        f"--concurrency={slots}",
        "-n",
        "scrape@%h",
    ]


def _demote() -> None:
    user = pwd.getpwnam(APP_USER)
    os.setgid(user.pw_gid)
    os.setuid(user.pw_uid)
    os.environ["HOME"] = user.pw_dir


def _prepare_data_dir() -> None:
    os.makedirs("/app/data", exist_ok=True)
    if os.geteuid() != 0:
        return
    user = pwd.getpwnam(APP_USER)
    os.chown("/app/data", user.pw_uid, user.pw_gid)


def _stop(procs: list[subprocess.Popen[bytes]], signum: int) -> None:
    for proc in procs:
        if proc.poll() is None:
            proc.send_signal(signum)


def main() -> int:
    _prepare_data_dir()
    preexec = _demote if os.geteuid() == 0 else None
    procs = [
        subprocess.Popen(cmd, preexec_fn=preexec, start_new_session=True)
        for cmd in (_MAINTENANCE, _scrape_command())
    ]
    signalled = False

    def _handle(signum: int, _frame: object) -> None:
        nonlocal signalled
        signalled = True
        _stop(procs, signum)

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)

    exit_code = 0
    while not signalled:
        finished = next((proc for proc in procs if proc.poll() is not None), None)
        if finished is not None:
            exit_code = finished.returncode or 1
            break
        time.sleep(2)

    _stop(procs, signal.SIGTERM)
    for proc in procs:
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)

    if signalled:
        return 0
    return exit_code or 1


if __name__ == "__main__":
    sys.exit(main())
