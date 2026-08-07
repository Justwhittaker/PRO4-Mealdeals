# Meal Deals API (FastAPI)

High-throughput, multi-region asynchronous backend for a global Meal Deals platform. Ingests, normalizes, localizes, and serves deals across English-speaking markets (US, UK, CA, AU, IE, NZ, SG, ZA, PH, IN, UAE, …).

## Stack

| Layer | Tech |
|-------|------|
| API | FastAPI (async), Python 3.12+ |
| DB | PostgreSQL 16 + PostGIS (`geoalchemy2`) |
| ORM | SQLAlchemy 2.0 async + Alembic |
| Cache / queue | Redis 7 + Celery |
| Scrapers | HTTPX, BeautifulSoup4, Playwright (stubs) |
| Runtime | Docker Compose |

## Quick start

```bash
cd backend

# Optional: copy env
cp .env.example .env

# Build & run API + Postgres/PostGIS + Redis + Celery
docker compose up --build
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)  
Health: [http://localhost:8000/health](http://localhost:8000/health)

### Migrations

Compose runs `alembic upgrade head` on API startup. Manually:

```bash
docker compose exec backend-api alembic upgrade head
# or locally with DATABASE_URL_SYNC set:
alembic upgrade head
```

### Tests

```bash
# Unit tests always run; spatial tests skip if PostGIS is down
pip install -r requirements.txt
pytest

# With live PostGIS (e.g. after docker compose up postgres)
DATABASE_URL_SYNC=postgresql://mealdeals:mealdeals@localhost:5432/mealdeals \
  pytest -m spatial -v
```

## Critical endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness |
| `GET` | `/go/{deal_id}` | Lookup `affiliate_url`, log click (Redis + Postgres), **302** redirect |
| `GET` | `/api/v1/deals/feed` | Geo feed: `country_code`, `city`, `lat`, `lon`, `radius_km`, `currency_override` — sorted by `feed_score` |
| `GET` | `/api/v1/deals/{deal_id}/value-calculator` | `SUM(individual_price) - deal_price` + savings % |
| `GET/POST/PATCH/DELETE` | `/api/v1/merchants` | Merchant CRUD |
| `GET/POST` | `/api/v1/geo/locations` | Locations + PostGIS nearby |

## Ranking (`feed_score`)

```
score = tier_weight + proximity + freshness - scrape_penalty + tier_priority_score
```

- **Enterprise** +1000 · **Featured** +500 · **Scraped/free** 0  
- **Proximity** up to +100, exponential decay with distance  
- **Freshness** up to +50 (72h half-life)  
- **Scrape penalty** −25 for non-subscriber free listings  

## Affiliate wrapping

`app/services/affiliate.py` strips tracking params for `clean_url`, then tags destinations for Amazon, Booking.com, Awin, CJ, Impact, and Rakuten using env-configurable publisher IDs.

## Celery beat (stubs)

| Schedule | Task |
|----------|------|
| Hourly `:15` | `update_currency_rates` |
| Every 6 hours | `scrape_global_retail` |

## Local (no Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL=postgresql+asyncpg://mealdeals:mealdeals@localhost:5432/mealdeals
export DATABASE_URL_SYNC=postgresql://mealdeals:mealdeals@localhost:5432/mealdeals
export REDIS_URL=redis://localhost:6379/0

alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Worker (separate shell)
celery -A app.workers.celery_app.celery_app worker --beat --loglevel=info
```

## Project layout

```
backend/
├── app/
│   ├── main.py
│   ├── api/v1/endpoints/   # deals, merchants, geo, redirect
│   ├── core/               # config, database, security
│   ├── models/             # locations, merchants, deals, translations, currencies
│   ├── schemas/
│   ├── services/           # affiliate, currency, ranking
│   ├── scrapers/
│   └── workers/            # Celery app + tasks
├── alembic/
├── tests/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Notes

- Bind address is always `0.0.0.0` (`HOST` / `PORT` env vars — Render-compatible).
- Filesystem is ephemeral in cloud deploys; persistent state belongs in Postgres/Redis.
- Scraper implementations are stubs suitable for CI; wire Playwright against live retailers when robots/ToS allow.
