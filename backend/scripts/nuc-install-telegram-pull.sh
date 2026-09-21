#!/usr/bin/env bash
# One-shot NUC install/refresh for Telegram /pull + /deploy.
# Run on the NUC as justinw (home LAN SSH). Safe to re-run.
set -euo pipefail

REPO="${MEALDEALS_REPO_DIR:-$HOME/MealDeals}"
SCRIPTS="$REPO/backend/scripts"
BRANCH="${GIT_BRANCH:-master}"
REMOTE="${GIT_REMOTE:-origin}"

echo "==> Repo: $REPO"
cd "$REPO"

if [[ ! -d .git ]]; then
  echo "ERROR: $REPO is not a git clone" >&2
  exit 1
fi

echo "==> git fetch + ff-only pull $REMOTE/$BRANCH"
git fetch --prune "$REMOTE" "$BRANCH"
git pull --ff-only "$REMOTE" "$BRANCH"
git rev-parse --short HEAD
git status -sb

echo "==> Repair-agent venv + deps"
cd "$SCRIPTS"
if [[ ! -d .venv-repair ]]; then
  python3 -m venv .venv-repair
fi
.venv-repair/bin/pip install -q -r requirements-repair-agent.txt

if [[ ! -f repair-agent.env ]]; then
  cp repair-agent.env.example repair-agent.env
  chmod 600 repair-agent.env
  echo "CREATED repair-agent.env — edit TELEGRAM_BOT_TOKEN + TELEGRAM_ALLOWED_USER_IDS before starting the bot."
  echo "  nano $SCRIPTS/repair-agent.env"
else
  # Ensure new keys exist (do not overwrite existing values)
  grep -q '^MEALDEALS_REPO_DIR=' repair-agent.env || \
    echo "MEALDEALS_REPO_DIR=$REPO" >> repair-agent.env
  grep -q '^GIT_REMOTE=' repair-agent.env || \
    echo "GIT_REMOTE=$REMOTE" >> repair-agent.env
  grep -q '^GIT_BRANCH=' repair-agent.env || \
    echo "GIT_BRANCH=$BRANCH" >> repair-agent.env
  grep -q '^PULL_COOLDOWN_SECS=' repair-agent.env || \
    echo "PULL_COOLDOWN_SECS=120" >> repair-agent.env
fi

echo "==> Recreate celery worker (nuc-up)"
cd "$REPO/backend"
if [[ -x scripts/nuc-up.sh ]]; then
  # nuc-up tails logs; run compose directly for non-interactive install
  docker compose -f docker-compose.nuc.yml up -d --build
else
  docker compose -f docker-compose.nuc.yml up -d --build
fi

echo "==> systemd user unit for repair-agent"
mkdir -p "$HOME/.config/systemd/user"
cp "$SCRIPTS/repair-agent.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now repair-agent.service
# Best-effort linger (may need password on some hosts)
loginctl enable-linger "$USER" 2>/dev/null || true

echo "==> Status"
systemctl --user --no-pager status repair-agent.service || true
docker ps --filter name=mealdeals-celery-nuc --format 'table {{.Names}}\t{{.Status}}' || true

echo
echo "Done. From Telegram: /help  /status  /pull  /deploy"
echo "Logs: journalctl --user -u repair-agent.service -f"
