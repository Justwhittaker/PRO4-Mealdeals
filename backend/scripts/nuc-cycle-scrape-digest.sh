#!/usr/bin/env bash
# Manually run the scrape-cycle ntfy digest inside mealdeals-celery-nuc.
# Normal delivery is Celery Beat at 05:50 and 17:50 UTC.
set -euo pipefail

CONTAINER="${CONTAINER:-mealdeals-celery-nuc}"

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -qx true; then
  echo "Container ${CONTAINER} is not running" >&2
  exit 1
fi

docker exec "$CONTAINER" celery -A app.workers.celery_app.celery_app call \
  app.workers.tasks.send_scrape_cycle_digest
