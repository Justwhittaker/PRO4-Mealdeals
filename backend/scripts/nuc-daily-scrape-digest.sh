#!/usr/bin/env bash
# Daily ntfy digest: new scraped deals in the last 24 hours.
# Reuses nuc-health.env (NTFY_*) by default.
set -euo pipefail

ENV_FILE="${ENV_FILE:-$HOME/MealDeals/backend/scripts/nuc-health.env}"
CONTAINER="${CONTAINER:-mealdeals-celery-nuc}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

: "${NTFY_TOPIC:?Set NTFY_TOPIC (see nuc-health.env)}"
NTFY_BASE="${NTFY_URL:-https://ntfy.sh}"
NTFY_BASE="${NTFY_BASE%/}"

notify() {
  local title="$1" body="$2" priority="${3:-default}" tags="${4:-chart_with_upwards_trend}"
  local -a hdr=(-H "Title: ${title}" -H "Priority: ${priority}" -H "Tags: ${tags}")
  [[ -n "${NTFY_TOKEN:-}" ]] && hdr+=(-H "Authorization: Bearer ${NTFY_TOKEN}")
  curl -fsS -o /dev/null "${hdr[@]}" -d "$body" "${NTFY_BASE}/${NTFY_TOPIC}" || true
}

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -qx true; then
  notify "MealDeals scrape digest FAILED" \
    "Container ${CONTAINER} is not running — cannot query deals." urgent warning
  exit 1
fi

# Python inside the celery image already has SQLAlchemy + DATABASE_URL_SYNC.
REPORT="$(docker exec "$CONTAINER" python - <<'PY'
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text

from app.core.config import get_settings

since = datetime.now(timezone.utc) - timedelta(hours=24)
engine = create_engine(get_settings().database_url_sync)
with engine.connect() as conn:
    total = conn.execute(
        text(
            """
            SELECT COUNT(*) FROM deals
            WHERE created_at >= :since
              AND deleted_at IS NULL
              AND scraped_raw_url IS NOT NULL
            """
        ),
        {"since": since},
    ).scalar_one()
    rows = conn.execute(
        text(
            """
            SELECT l.country_code, l.city, COUNT(*) AS n
            FROM deals d
            JOIN merchants m ON m.id = d.merchant_id
            JOIN locations l ON l.id = m.location_id
            WHERE d.created_at >= :since
              AND d.deleted_at IS NULL
              AND d.scraped_raw_url IS NOT NULL
            GROUP BY l.country_code, l.city
            ORDER BY n DESC
            LIMIT 15
            """
        ),
        {"since": since},
    ).all()

print(f"NEW_DEALS={total}")
print("BREAKDOWN_BEGIN")
for country, city, n in rows:
    print(f"{country}\t{city}\t{n}")
print("BREAKDOWN_END")
PY
)"

NEW_DEALS="$(printf '%s\n' "$REPORT" | sed -n 's/^NEW_DEALS=//p' | head -1)"
NEW_DEALS="${NEW_DEALS:-0}"

BREAKDOWN="$(printf '%s\n' "$REPORT" | sed -n '/^BREAKDOWN_BEGIN$/,/^BREAKDOWN_END$/p' | sed '1d;$d')"
if [[ -z "$BREAKDOWN" ]]; then
  BODY="New scraped deals (last 24h): ${NEW_DEALS}

No city breakdown (none found)."
else
  TABLE="$(printf '%s\n' "$BREAKDOWN" | awk -F'\t' '{printf "%s / %s: %s\n", $1, $2, $3}')"
  BODY="New scraped deals (last 24h): ${NEW_DEALS}

Top cities:
${TABLE}"
fi

notify "MealDeals daily scrape digest" "$BODY" default chart_with_upwards_trend
echo "$BODY"
