#!/usr/bin/env python3
"""Run the NUC scrape worker and the maintenance/beat worker in one container.

Zone scrapes sit on the ``scrape`` queue. Digest, expiry, and currency tasks
sit on ``maintenance`` so a multi-hour scrape cannot block them. This process
is PID 1: it drops to ``appuser`` for the workers and forwards stop signals.
"""

from __future__ import annotations

import os
import pwd
import signal
import subprocess
import sys
import time

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
# ``celery`` is the old default queue. Keep draining it so a restart does not
# strand zone tasks Beat already published before this split.
_SCRAPE = [
    *_CELERY,
    "--loglevel=info",
    "-Q",
    "scrape,celery",
    "--concurrency=2",
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
        for cmd in (_MAINTENANCE, _SCRAPE)
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
