"""Load repair-agent.env into a typed config."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    allowed_user_ids: frozenset[int]
    backend_dir: Path
    compose_file: str
    container: str
    restart_cooldown_secs: int
    ntfy_topic: str | None
    ntfy_url: str
    ntfy_token: str | None
    log_tail_lines: int

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> Config:
        default_env = (
            Path.home() / "MealDeals" / "backend" / "scripts" / "repair-agent.env"
        )
        path = env_file or Path(
            os.environ.get("REPAIR_AGENT_ENV", str(default_env))
        )
        _load_env_file(path)

        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise SystemExit(
                "TELEGRAM_BOT_TOKEN is required (see repair-agent.env.example)"
            )

        raw_ids = os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "").strip()
        if not raw_ids:
            raise SystemExit(
                "TELEGRAM_ALLOWED_USER_IDS is required (comma-separated Telegram user ids)"
            )
        allowed = frozenset(int(x.strip()) for x in raw_ids.split(",") if x.strip())
        if not allowed:
            raise SystemExit("TELEGRAM_ALLOWED_USER_IDS parsed empty")

        backend = Path(
            os.environ.get(
                "MEALDEALS_BACKEND_DIR",
                str(Path.home() / "MealDeals" / "backend"),
            )
        ).expanduser()

        ntfy_topic = os.environ.get("NTFY_TOPIC", "").strip() or None

        return cls(
            telegram_bot_token=token,
            allowed_user_ids=allowed,
            backend_dir=backend,
            compose_file=os.environ.get(
                "COMPOSE_FILE", "docker-compose.nuc.yml"
            ).strip(),
            container=os.environ.get("CONTAINER", "mealdeals-celery-nuc").strip(),
            restart_cooldown_secs=int(
                os.environ.get("RESTART_COOLDOWN_SECS", "300")
            ),
            ntfy_topic=ntfy_topic,
            ntfy_url=os.environ.get("NTFY_URL", "https://ntfy.sh").rstrip("/"),
            ntfy_token=os.environ.get("NTFY_TOKEN", "").strip() or None,
            log_tail_lines=int(os.environ.get("LOG_TAIL_LINES", "40")),
        )
