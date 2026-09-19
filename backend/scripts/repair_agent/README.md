# NUC Telegram repair bot ($0 — no LLM)

Slash commands from your phone: `/status`, `/restart`, `/logs`, `/host`.
Health pushes stay on **ntfy** via `nuc-celery-health.sh`.

## One-time setup

### 1. Create the bot
1. Open Telegram → **@BotFather** → `/newbot`
2. Copy the token
3. Message **@userinfobot** and copy your numeric user id

### 2. Copy files from Mac
```bash
ssh justinw@192.168.1.171 'mkdir -p ~/MealDeals/backend/scripts/repair_agent'
scp -r /Users/justinw/Projects/JustinBot/MealDeals/backend/scripts/repair_agent \
  /Users/justinw/Projects/JustinBot/MealDeals/backend/scripts/repair-agent.env.example \
  /Users/justinw/Projects/JustinBot/MealDeals/backend/scripts/repair-agent.service \
  justinw@192.168.1.171:~/MealDeals/backend/scripts/
# then move nested copy if scp put repair_agent inside scripts twice — prefer:
# scp files into ~/MealDeals/backend/scripts/ as listed in INSTALL steps below
```

Simpler from Mac:
```bash
rsync -av /Users/justinw/Projects/JustinBot/MealDeals/backend/scripts/repair_agent \
  /Users/justinw/Projects/JustinBot/MealDeals/backend/scripts/repair-agent.env.example \
  /Users/justinw/Projects/JustinBot/MealDeals/backend/scripts/repair-agent.service \
  justinw@192.168.1.171:~/MealDeals/backend/scripts/
```

### 3. On the NUC
```bash
cd ~/MealDeals/backend/scripts
cp repair-agent.env.example repair-agent.env
nano repair-agent.env   # set TELEGRAM_BOT_TOKEN + TELEGRAM_ALLOWED_USER_IDS
# optional: copy NTFY_TOPIC from nuc-health.env
chmod 600 repair-agent.env

# smoke test (Ctrl+C after /status works)
PYTHONPATH=$HOME/MealDeals/backend/scripts \
  REPAIR_AGENT_ENV=$HOME/MealDeals/backend/scripts/repair-agent.env \
  python3 -m repair_agent.bot
```

### 4. systemd (survives logout)
```bash
mkdir -p ~/.config/systemd/user
cp ~/MealDeals/backend/scripts/repair-agent.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now repair-agent.service
loginctl enable-linger "$USER"
systemctl --user status repair-agent.service
```

Logs: `journalctl --user -u repair-agent.service -f`

## Commands
| Command | Action |
|---------|--------|
| `/status` | Docker running + Celery ping |
| `/restart` | `docker compose -f docker-compose.nuc.yml up -d --force-recreate` (5 min cooldown) |
| `/logs` | Tail container logs |
| `/host` | `df` / `free` |

Stdlib only — no pip packages.
