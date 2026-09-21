# NUC Telegram repair bot ($0 — no LLM)

Slash commands only: `/status`, `/restart`, `/logs`, `/disk`, `/help`.
Works with the existing ntfy health cron; optionally posts an ntfy ack on `/restart`.

## 1. Create the Telegram bot

1. Open Telegram → talk to [@BotFather](https://t.me/BotFather)
2. `/newbot` → copy the token
3. Message [@userinfobot](https://t.me/userinfobot) → copy your numeric **Id**

## 2. Copy files to the NUC (from your Mac)

```bash
ssh justinw@192.168.1.171 'mkdir -p ~/MealDeals/backend/scripts'
scp -r backend/scripts/repair_agent \
  backend/scripts/repair-agent.env.example \
  backend/scripts/repair-agent.service \
  backend/scripts/requirements-repair-agent.txt \
  backend/scripts/README-repair-agent.md \
  justinw@192.168.1.171:~/MealDeals/backend/scripts/
```

(Adjust paths if your local MealDeals clone differs.)

## 3. On the NUC — venv + env

```bash
cd ~/MealDeals/backend/scripts
python3 -m venv .venv-repair
.venv-repair/bin/pip install -r requirements-repair-agent.txt

cp repair-agent.env.example repair-agent.env
nano repair-agent.env   # set TELEGRAM_BOT_TOKEN + TELEGRAM_ALLOWED_USER_IDS
# Optional: copy NTFY_TOPIC from nuc-health.env for restart acks
chmod 600 repair-agent.env
```

Smoke test (Ctrl+C to stop):

```bash
cd ~/MealDeals/backend/scripts
REPAIR_AGENT_ENV=$PWD/repair-agent.env .venv-repair/bin/python -m repair_agent.bot
```

In Telegram, message your bot: `/status`

## 4. systemd (survives logout)

```bash
mkdir -p ~/.config/systemd/user
cp ~/MealDeals/backend/scripts/repair-agent.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now repair-agent.service
loginctl enable-linger justinw   # keep user services after SSH logout

systemctl --user status repair-agent.service
journalctl --user -u repair-agent.service -f
```

## Commands

| Command | Action |
|---------|--------|
| `/status` | Docker running + Celery ping |
| `/restart` | Recreate celery worker (rate-limited) + post status; optional ntfy ack |
| `/logs` | Tail container logs |
| `/disk` | Disk + memory |
| `/help` | Command list |

## Security

- Only `TELEGRAM_ALLOWED_USER_IDS` can run commands
- No free-text LLM / no arbitrary shell
- `/restart` rate-limited (`RESTART_COOLDOWN_SECS`, default 300)
- Never commit `repair-agent.env`
