# NUC Telegram repair bot ($0 — no LLM)

Slash commands from your phone: `/status`, `/pull`, `/deploy`, `/restart`, `/logs`, `/disk`, `/help`.
Health pushes stay on **ntfy** via `nuc-celery-health.sh`.

See [../README-repair-agent.md](../README-repair-agent.md) for full install.

## Commands
| Command | Action |
|---------|--------|
| `/status` | Docker running + Celery ping |
| `/pull` | `git fetch` + `git pull --ff-only` (allowlisted remote/branch) |
| `/deploy` | `/pull` then recreate celery-worker |
| `/restart` | `docker compose … up -d --force-recreate` (cooldown) |
| `/logs` | Tail container logs |
| `/disk` | `df` / `free` |
