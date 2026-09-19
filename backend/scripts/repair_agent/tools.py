"""Allowlisted Docker/Celery actions — no arbitrary shell from user input."""

from __future__ import annotations

import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from repair_agent.config import Config

_LAST_RESTART_AT = 0.0


@dataclass
class ToolResult:
    ok: bool
    text: str


def _run(
    args: list[str],
    *,
    cwd: str | None = None,
    timeout: int = 60,
) -> ToolResult:
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(ok=False, text=f"Timed out after {timeout}s: {' '.join(args)}")
    except OSError as exc:
        return ToolResult(ok=False, text=f"Failed to run command: {exc}")

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    body = out if out else err
    if proc.returncode != 0:
        detail = body or f"exit {proc.returncode}"
        return ToolResult(ok=False, text=detail)
    return ToolResult(ok=True, text=body or "(no output)")


def celery_status(cfg: Config) -> ToolResult:
    inspect = _run(
        [
            "docker",
            "inspect",
            "-f",
            "running={{.State.Running}} status={{.State.Status}} "
            "started={{.State.StartedAt}}",
            cfg.container,
        ],
        timeout=15,
    )
    lines = [f"container: {cfg.container}", inspect.text]
    if not inspect.ok:
        return ToolResult(ok=False, text="\n".join(lines))

    ping = _run(
        [
            "docker",
            "exec",
            cfg.container,
            "celery",
            "-A",
            "app.workers.celery_app.celery_app",
            "inspect",
            "ping",
            "-t",
            "10",
        ],
        timeout=30,
    )
    lines.append("celery ping:")
    lines.append(ping.text)
    return ToolResult(ok=inspect.ok and ping.ok, text="\n".join(lines))


def celery_logs(cfg: Config) -> ToolResult:
    return _run(
        ["docker", "logs", "--tail", str(cfg.log_tail_lines), cfg.container],
        timeout=30,
    )


def celery_restart(cfg: Config) -> ToolResult:
    global _LAST_RESTART_AT
    now = time.time()
    elapsed = now - _LAST_RESTART_AT
    if _LAST_RESTART_AT and elapsed < cfg.restart_cooldown_secs:
        wait = int(cfg.restart_cooldown_secs - elapsed)
        return ToolResult(
            ok=False,
            text=f"Restart cooldown: wait {wait}s (max 1 per {cfg.restart_cooldown_secs}s).",
        )

    compose_path = cfg.backend_dir / cfg.compose_file
    if not compose_path.is_file():
        return ToolResult(
            ok=False,
            text=f"Compose file not found: {compose_path}",
        )

    result = _run(
        [
            "docker",
            "compose",
            "-f",
            cfg.compose_file,
            "up",
            "-d",
            "--force-recreate",
        ],
        cwd=str(cfg.backend_dir),
        timeout=180,
    )
    if result.ok:
        _LAST_RESTART_AT = now
        ntfy_ack(cfg, "MealDeals Celery restart", f"Restarted {cfg.container} via Telegram")
    return result


def disk_memory(_cfg: Config) -> ToolResult:
    disk = _run(["df", "-h", "/"], timeout=10)
    mem = _run(["free", "-h"], timeout=10)
    parts = ["=== disk ===", disk.text, "", "=== memory ===", mem.text]
    ok = disk.ok and mem.ok
    return ToolResult(ok=ok, text="\n".join(parts))


def ntfy_ack(cfg: Config, title: str, body: str) -> None:
    if not cfg.ntfy_topic:
        return
    url = f"{cfg.ntfy_url}/{cfg.ntfy_topic}"
    headers = {
        "Title": title,
        "Priority": "default",
        "Tags": "wrench",
    }
    if cfg.ntfy_token:
        headers["Authorization"] = f"Bearer {cfg.ntfy_token}"
    req = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        pass
