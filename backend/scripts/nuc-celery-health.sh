#!/usr/bin/env bash
# Cron-friendly health check for mealdeals-celery-nuc → ntfy phone alerts.
# Env: NTFY_TOPIC (required), NTFY_URL, NTFY_TOKEN, CHECK_CELERY=1, REMINDER_HOURS=1
set -euo pipefail

CONTAINER="${CONTAINER:-mealdeals-celery-nuc}"
ENV_FILE="${ENV_FILE:-$HOME/MealDeals/backend/scripts/nuc-health.env}"
STATE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/mealdeals-nuc-health"
STATE_FILE="$STATE_DIR/celery.state"
CHECK_CELERY="${CHECK_CELERY:-1}"
REMINDER_HOURS="${REMINDER_HOURS:-1}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

: "${NTFY_TOPIC:?Set NTFY_TOPIC (see nuc-health.env.example)}"
NTFY_BASE="${NTFY_URL:-https://ntfy.sh}"
NTFY_BASE="${NTFY_BASE%/}"
REMINDER_SECS=$((REMINDER_HOURS * 3600))

notify() {
  local title="$1" body="$2" priority="${3:-default}" tags="${4:-}"
  local -a hdr=(-H "Title: ${title}" -H "Priority: ${priority}")
  [[ -n "$tags" ]] && hdr+=(-H "Tags: ${tags}")
  [[ -n "${NTFY_TOKEN:-}" ]] && hdr+=(-H "Authorization: Bearer ${NTFY_TOKEN}")
  curl -fsS -o /dev/null "${hdr[@]}" -d "$body" "${NTFY_BASE}/${NTFY_TOPIC}" || true
}

healthy() {
  local running
  running="$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || echo false)"
  [[ "$running" == "true" ]] || return 1
  if [[ "$CHECK_CELERY" == "1" ]]; then
    docker exec "$CONTAINER" \
      celery -A app.workers.celery_app.celery_app inspect ping -t 10 \
      >/dev/null 2>&1 || return 1
  fi
  return 0
}

mkdir -p "$STATE_DIR"
prev="ok"
last_alert=0
if [[ -f "$STATE_FILE" ]]; then
  read -r prev last_alert <"$STATE_FILE" || true
  prev="${prev:-ok}"
  last_alert="${last_alert:-0}"
fi
now="$(date +%s)"

if healthy; then
  if [[ "$prev" != "ok" ]]; then
    notify "MealDeals Celery recovered" \
      "${CONTAINER} is healthy again on $(hostname -s)" default white_check_mark
  fi
  printf 'ok %s\n' "$now" >"$STATE_FILE"
  exit 0
fi

# Down: alert on ok→fail transition, or every REMINDER_HOURS while still down
alert=0
if [[ "$prev" == "ok" ]] || (( now - last_alert >= REMINDER_SECS )); then
  alert=1
fi
if (( alert )); then
  notify "MealDeals Celery DOWN" \
    "${CONTAINER} failed on $(hostname -s) (running/ping check)" urgent "warning,skull"
  printf 'fail %s\n' "$now" >"$STATE_FILE"
else
  printf 'fail %s\n' "$last_alert" >"$STATE_FILE"
fi
exit 1
