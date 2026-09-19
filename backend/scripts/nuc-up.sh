#!/usr/bin/env bash
# Start (or restart) the always-on NUC Celery worker + Beat.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing $ROOT/.env"
  echo "  cp .env.nuc.example .env"
  echo "  # then paste Render External DATABASE_URL_SYNC + Redis URLs + REVALIDATE_SECRET"
  exit 1
fi

mkdir -p data
docker compose -f docker-compose.nuc.yml up -d --build
echo ""
echo "Celery + Beat started. Logs:"
docker compose -f docker-compose.nuc.yml logs -f --tail=80 celery-worker
