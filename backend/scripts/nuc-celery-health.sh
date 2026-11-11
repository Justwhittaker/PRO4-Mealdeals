#!/usr/bin/env bash
# Cron-friendly health check for mealdeals-celery-nuc → ntfy phone alerts.
# Env: NTFY_TOPIC (required), NTFY_URL, NTFY_TOKEN, CHECK_CELERY=1, REMINDER_HOURS=1
#      CELERY_HEALTH_FAIL_THRESHOLD=2 (consecutive failed runs before a DOWN alert)
#      CELERY_HEALTH_PING_RETRY_SLEEP=5 (one in-run retry after a failed ping)
#      CELERY_HEALTH_VERBOSE=0 (1 = print masked command output when a command fails)
#
# State file ($STATE_DIR/celery.state), one line:
#   <ok|pending|fail> <last_alert_epoch> <consecutive_failures>
# Legacy two-field lines ("<ok|fail> <epoch>") still parse. A legacy "fail" line
# means a DOWN alert was already sent, so recovery and reminders still apply.
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
FAIL_THRESHOLD="${CELERY_HEALTH_FAIL_THRESHOLD:-2}"
PING_RETRY_SLEEP="${CELERY_HEALTH_PING_RETRY_SLEEP:-5}"
if [[ ! "$FAIL_THRESHOLD" =~ ^[1-9][0-9]*$ ]]; then
  FAIL_THRESHOLD=2
fi
if [[ ! "$PING_RETRY_SLEEP" =~ ^[0-9]+$ ]]; then
  PING_RETRY_SLEEP=5
fi

# redis:// and rediss:// URLs can carry a password. Never print them.
mask_secrets() {
  sed -E 's#(rediss?://)[^[:space:]]*#\1***#g'
}

notify() {
  local title="$1" body="$2" priority="${3:-default}" tags="${4:-}"
  local -a hdr=(-H "Title: ${title}" -H "Priority: ${priority}")
  body="$(printf '%s' "$body" | mask_secrets)"
  [[ -n "$tags" ]] && hdr+=(-H "Tags: ${tags}")
  [[ -n "${NTFY_TOKEN:-}" ]] && hdr+=(-H "Authorization: Bearer ${NTFY_TOKEN}")
  curl -fsS -o /dev/null "${hdr[@]}" -d "$body" "${NTFY_BASE}/${NTFY_TOPIC}" || true
}

# Keep command output off the console. Verbose mode prints a failure with
# broker URLs masked, so cron stays quiet unless someone opts in.
run_quiet() {
  local out rc
  set +e
  out="$("$@" 2>&1)"
  rc=$?
  set -e
  if (( rc != 0 )) && [[ "${CELERY_HEALTH_VERBOSE:-0}" == "1" && -n "$out" ]]; then
    printf '%s\n' "$out" | mask_secrets >&2 || true
  fi
  return "$rc"
}

celery_ping() {
  run_quiet docker exec "$CONTAINER" \
    celery -A app.workers.celery_app.celery_app inspect ping -t 10
}

healthy() {
  local running
  running="$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || echo false)"
  [[ "$running" == "true" ]] || return 1
  if [[ "$CHECK_CELERY" == "1" ]]; then
    if ! celery_ping; then
      if (( PING_RETRY_SLEEP > 0 )); then
        sleep "$PING_RETRY_SLEEP"
      fi
      celery_ping || return 1
    fi
  fi
  return 0
}

write_state() {
  printf '%s %s %s\n' "$1" "$2" "$3" >"$STATE_FILE"
}

mkdir -p "$STATE_DIR"
prev="ok"
last_alert=0
fail_streak=0
if [[ -f "$STATE_FILE" ]]; then
  read -r prev last_alert fail_streak _ <"$STATE_FILE" || true
fi
prev="${prev:-ok}"
[[ "${last_alert:-}" =~ ^[0-9]+$ ]] || last_alert=0
# Legacy "fail <epoch>" has no streak column; DOWN was already sent.
if [[ ! "${fail_streak:-}" =~ ^[0-9]+$ ]]; then
  if [[ "$prev" == "fail" ]]; then
    fail_streak="$FAIL_THRESHOLD"
  else
    fail_streak=0
  fi
fi
alerted=0
[[ "$prev" == "fail" ]] && alerted=1
now="$(date +%s)"

if healthy; then
  # Recovery only if a DOWN alert was actually sent.
  if (( alerted )); then
    notify "MealDeals Celery recovered" \
      "${CONTAINER} is healthy again on $(hostname -s)" default white_check_mark
  fi
  write_state ok "$now" 0
  exit 0
fi

fail_streak=$((fail_streak + 1))

send_down=0
if (( alerted )); then
  if (( now - last_alert >= REMINDER_SECS )); then
    send_down=1
  fi
elif (( fail_streak >= FAIL_THRESHOLD )); then
  send_down=1
fi

if (( send_down )); then
  notify "MealDeals Celery DOWN" \
    "${CONTAINER} failed on $(hostname -s) (running/ping check)" urgent "warning,skull"
  write_state fail "$now" "$fail_streak"
elif (( alerted )); then
  write_state fail "$last_alert" "$fail_streak"
else
  write_state pending 0 "$fail_streak"
fi
exit 1
