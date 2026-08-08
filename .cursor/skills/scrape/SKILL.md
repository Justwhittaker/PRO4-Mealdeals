---
name: scrape
description: >-
  Starts the MealDeals hospitality scrape rule and runs a fresh worldwide
  scrape refresh that upserts deals and marketing business contacts, corrects
  deal/logo image scraping, then updates the MealDeals website and metrics
  canvas with the newest data. Use when the user invokes /scrape, asks to
  refresh scrapes, or wants a new scrape pass.
disable-model-invocation: true
---

# /scrape — fresh hospitality scrape

## Goal

Start the hospitality scraping rule and run a **fresh scrape** across **all**
`TARGET_MARKETS` (currently 91 countries / 383 cities). Persist deals and a
separate marketing contact ledger, **update the MealDeals website so it serves
the newest scraped data**, refresh the metrics canvas, then **show the full
results breakdown** to the user.

**Project root:** workspace `PRO4-Mealdeals` / `backend` (+ `frontend`).

## Before scraping

1. Read and follow `.cursor/rules/hospitality-deal-scraping.mdc`.
2. Confirm Docker API is up (`mealdeals-api` on `:8000`) or start `backend` via `docker compose`.
3. Apply migrations:

```bash
docker exec mealdeals-api alembic upgrade head
```

## Markets in scope

Always scrape the full `TARGET_MARKETS` list from `backend/app/scrapers/markets.py`
(do **not** pass `only_new=true`). That list includes the seed markets
(GB, US, CA, AU, IE, NZ, PH, TH, NL, BS, JM) plus every expanded market
(Caribbean, Africa, Europe, MENA, Asia, LatAm, Pacific, etc.).

Country search UI reads `frontend/lib/markets-catalog.ts` (generated from
`TARGET_MARKETS` / `MARKET_CITIES`). If markets change, regenerate that file
and keep `GET /api/v1/geo/markets` in sync.

## Start the fresh scrape

Prefer a **synchronous** run so the response includes the full report:

```bash
curl -sS -X POST 'http://localhost:8000/api/v1/scrapers/scrape?wait=true'
```

This can take several minutes. Raise the curl max-time if needed:

```bash
curl -sS --max-time 1200 -X POST 'http://localhost:8000/api/v1/scrapers/scrape?wait=true'
```

If you must queue async:

```bash
curl -sS -X POST 'http://localhost:8000/api/v1/scrapers/scrape?wait=false'
docker restart mealdeals-celery   # if worker was restarted recently
# poll until complete, then:
curl -sS 'http://localhost:8000/api/v1/scrapers/report'
```

## What the scrape must capture

| Field | Required | Destination |
|-------|----------|-------------|
| Business name | yes | `marketing_contacts.business_name` + deal merchant |
| Website | yes (fallback source URL) | `marketing_contacts.website` |
| Telephone | when found | `marketing_contacts.phone` |
| Email | when found | `marketing_contacts.email` |
| About blurb | when About / description available | `marketing_contacts.about_blurb` |
| Venue category | yes (auto-tagged via parent taxonomy) | `marketing_contacts.venue_category` |
| Deal image (`img` / `png` / jpg / webp) | yes (see image scrape rules) | `deals.image_url` / scraped `image_url` |
| Company logo | yes when found | merchant / scraped `logo_url` (persist + expose to frontend) |

Also capture deal inventory per the hospitality rule.

## Image + logo scrape — REQUIRED (FORCE photo order)

**FORCE RULE — never skip steps.** Every deal photo must attempt, in order:

1. **Deal / offer page** for that specific listing  
2. **Merchant website landing / menu** pages on the same origin  
3. **Dish-category generic placeholder** (last resort only)

Never prefer a generic/stock photo when a real merchant-site photo exists.
Never use the company logo as the deal hero.

### Why generics still appear

When live HTML is blocked / JS-only / missing images, step 3 uses
`backend/app/scrapers/deal_placeholders.py`: burgers, pasta, pizza, sushi,
vineyard wine, hotel dining, tagine, curry, etc. matched from title /
description / items / venue category. Unknown dishes (e.g. a new “tagine”
deal) can be learned via Wikimedia Commons search and persisted in
`backend/app/scrapers/data/dish_placeholders.json` for future scrapes.

### 1. Deal photo from the offer page (primary)

- Pull the deal image from the deal/offers URL: hero/promo/menu/food `<img>`
  (including `srcset`, `data-src`, `data-lazy-src`), then `og:image` /
  `twitter:image`, then JSON-LD `image`.
- Accept CDN raster URLs (`.png` / `.jpg` / `.jpeg` / `.webp`, or extensionless).
- **Exclude** logo/favicon/icon assets from the deal hero.
- Persist on the deal as `image_url`.

### 2. Fallback photo from elsewhere on the site

- If the offer page has no usable photo, fetch the same origin’s `/`, `/menu`,
  `/our-menu`, `/menus`, `/food`, `/about` and extract a large content photo.
- Prefer real food/menu/hero photos over icons, sprites, pixels, tracking GIFs.

### 3. Dish-category generic (last resort)

- Call `resolve_dish_placeholder(...)` with `discover_unknown=True`.
- Match dish keywords first; else venue default (wine farm → vineyard wine,
  hotel → hotel dining, pub → pub food, deli → grocery, etc.).
- If still unknown, search Wikimedia for a generic of that dish name, save it
  under `dish_placeholders.json`, and reuse going forward.
- Log: `No site image for X — dish placeholder 'burger'` (etc.).

### 3. Company logo (separate from hero)

- Extract the **brand logo** (e.g. Nando’s rooster): header `<img>` with
  logo/brand/wordmark, JSON-LD `logo`, then apple-touch-icon / favicon.
- Persist as `merchants.logo_url` (via `ScrapedDeal.logo_url`) — **never** as
  the deal hero `image_url`.

### 4. Business about blurb

- Capture About / JSON-LD / meta description into `about_blurb` →
  `marketing_contacts.about_blurb` **and** `merchants.bio`.
- Deal detail UI shows this as a small paragraph **under the Website** link
  (`about_blurb` / `aboutBlurb`), separate from the deal offer description.

### 5. Deal page + feed UI — circular logo insert

On deal detail, homepage `DealCard`, and advert carousel:

- Main image = scraped `image_url`.
- Company logo = circular overlay at **bottom-left** of the hero
  (`DealHeroMedia`, `rounded-full`, white border).
- If `logo_url` is missing, omit the circle (do not invent a logo).

### Implementation touchpoints

- Scraper: `backend/app/scrapers/global_retail.py`
  (`_extract_deal_image_url`, `_extract_logo_url`, `_fetch_site_media`).
- Ingest: `image_url` → deal; `logo_url` + `about_blurb` → merchant.
- API: feed/detail return `logo_url`; detail also returns `about_blurb`.
- UI: `DealHeroMedia` on detail + cards + `AdvertCarousel`.
- After fixing image/logo logic, **re-run `/scrape`** so existing Unsplash
  placeholders get replaced with site photos.

## Venue category taxonomy (required)

Tag every venue with **one parent** from `backend/app/scrapers/categories.py`
(`categorize_venue` / `CATEGORY_ORDER`). The MealDeals UI category filter uses
the same six parents (`frontend/lib/categories.ts`).

### Parent filters

1. Restaurants, Cafe's & Bistro's
2. Food Trucks & Takeaway's
3. Wine Farms & Entertainment Venues
4. Deli's and Grocers
5. Clubs, Bars & Pubs
6. Hotels, Resorts & B&B's

### Subcategories grouped under parents

Full grouping lives in `CATEGORY_GROUPS` in `backend/app/scrapers/categories.py`
and is mirrored in `.cursor/skills/scrape/category-taxonomy.md`. When tagging or
reporting, use the **parent** label in `venue_category` / scrape tallies (not
the leaf subcategory), unless a future scrape stores both.

Do not invent new parent buckets. Map new venue types into the closest parent.

## Wine Farms & Entertainment — REQUIRED pack + tagging

Wine farms were historically empty because no cellar-door merchants were seeded
(the only “Wine Farms” rows were false positives like grocery **Casino Cameroon**
matching bare `casino`). Every `/scrape` must keep wine-farm coverage real.

### Source pack

- Maintain `WINE_FARM_PACK` in `backend/app/scrapers/hospitality_pack.py`.
- It is merged via `hospitality_sources_for` / `merge_hospitality_into_sources`
  into full `TARGET_MARKETS` scrapes (same as hotels/pubs).
- Priority wine markets (seed ~3–5 real cellar-door / tasting-lunch URLs each):
  **ZA, US, AU, NZ, FR, IT, ES, PT, CL, AR, DE, GB**.
- Merchant names **must** include tokens that categorize cleanly:
  `Wine Farm`, `Wine Estate`, `Vineyard`, `Winery`, `Cellar Door`, `Domaine`,
  `Château`, `Bodega`, `Weingut`, `Quinta`, etc.
- Prefer F&B pages (eat/drink, restaurant, tasting lunch, cellar door) — not
  pure retail wine shops with no dining.
- Do **not** invent placeholder venues (e.g. wine-searcher directories) as merchants.

### Tagging rules (keep backend + frontend in sync)

- Backend: `backend/app/scrapers/categories.py`
- Frontend: `frontend/lib/categories.ts`
- Prefer vineyard / winery / cellar-door / domaine / château / bodega / weingut
  / cantina / quinta / wine tasting for this parent.
- Do **not** classify bare `casino` as entertainment (grocery FP). Use
  `casino (restaurant|resort|hotel|bar|dining|cafe)` only.
- Route grocery Casino brands (`Casino Cameroon`, `Casino Supermarket`,
  `Groupe Casino`, etc.) into **Deli's and Grocers**.

### Optional discovery (heavier)

When Justin asks to grow wine-farm inventory beyond the pack: for wine-region
cities, crawl tourism / “cellar door lunch” directories, keep only F&B offer
pages, append real `{merchant, url}` rows into `WINE_FARM_PACK`, then re-scrape.
Never invent non-F&B merchants.

### Verify wine-farm slice

After scrape, check `category_tally` for **Wine Farms & Entertainment Venues**
(should be >> 0 and not dominated by grocery false positives). Spot-check ZA /
US / FR / AU merchants in the feed or `marketing_contacts`.

## After scrape — REQUIRED website + metrics refresh

**Always** push the newest scrape into the live MealDeals website and metrics
UI before reporting to the user. Do not end `/scrape` until this is done.

1. **Keep category taxonomy in sync** so filters/cards match the scrape:
   - Backend: `backend/app/scrapers/categories.py`
   - Frontend: `frontend/lib/categories.ts`
   - If brand rules or parents changed during the scrape pass, update the
     frontend rules to match before verifying pages.
2. **Ensure the Next.js site is serving fresh data**:
   - Confirm `frontend` is up on `:3000` (`npm run dev` in `frontend/` if down).
   - Hit a sample area page (e.g. `http://localhost:3000/gb/london`) and confirm
     newly scraped merchants appear in the HTML/feed.
   - If the page looks stale, restart the frontend (`npm run dev`) and re-check.
   - Deals come from the API DB — after a successful ingest, the site must show
     that inventory; do not leave the user on old scraped data.
3. **Refresh the metrics inspection canvas** with the latest report snapshot:
   - Source: `GET /api/v1/scrapers/report` (or the scrape response `report`).
   - Update
     `~/.cursor/projects/Users-justinw-Projects-justin-bot/canvases/scrape-metrics-inspection.canvas.tsx`
     (create it if missing) with embedded newest summary, `category_tally`,
     `by_country`, and `breakdown`.
   - Open the canvas for the user.
4. **Optional but preferred:** export marketing CSV for the refreshed pass:

```bash
curl -sS 'http://localhost:8000/api/v1/marketing/contacts/export' -o marketing_contacts.csv
```

## After scrape — REQUIRED user report

Parse the JSON (`report` object, or `GET /api/v1/scrapers/report`) and **always**
render these three markdown tables to the user. Do not skip or summarize away
the breakdown tables.

### 1. Summary metrics

| Metric | Result |
|--------|--------|
| Areas | `{summary.areas}` cities |
| Markets | `{summary.markets}` countries |
| Deals discovered / ingested | `{summary.deals_discovered}` / `{summary.deals_ingested}` |
| Marketing contacts upserted | `{summary.marketing_contacts_upserted}` (`{summary.marketing_contacts_unique}` unique in DB) |
| Runtime | `{summary.runtime_seconds}`s |

Example shape:

| Metric | Result |
|--------|--------|
| Areas | 383 cities |
| Markets | 91 countries |
| Deals discovered / ingested | 1000 / 1000 |
| Marketing contacts upserted | 1000 (973 unique in DB) |
| Runtime | 322s |

### 2. Breakdown by country → city → category

Render a table from `report.breakdown` (or top-level `breakdown`):

| Country | City | Category | Deals |
|---------|------|----------|-------|
| GB | London | Restaurants, Cafe's & Bistro's | 12 |
| … | … | … | … |

Include **all** rows returned (country, city, category, deals). If the table is
very long, still show it in full (or attach via a file) — do not collapse to
country-only totals unless the user asks.

### 3. Category tally

Render a separate table from `report.category_tally`:

| Category | Deals |
|----------|-------|
| Restaurants, Cafe's & Bistro's | 240 |
| Food Trucks & Takeaway's | 180 |
| … | … |

### 4. Show

After the tables, briefly note marketing CSV export is available and that
contacts live in `marketing_contacts` (separate from `merchants` / `deals`).

## Marketing export

- List: `GET /api/v1/marketing/contacts`
- CSV: `GET /api/v1/marketing/contacts/export`
- Live report snapshot: `GET /api/v1/scrapers/report`

```bash
curl -sS 'http://localhost:8000/api/v1/marketing/contacts/export' -o marketing_contacts.csv
```

## Verify

1. Response `status` is `completed` (or Celery log shows `Worldwide scrape complete`).
2. `markets` length matches full `TARGET_MARKETS` (not a subset).
3. Website sample page shows newest scraped merchants (not a stale feed).
4. Sample deal pages show site-sourced deal photos when available (not Unsplash
   when the merchant site has food/menu imagery), circular bottom-left company
   logo when `logo_url` exists, and business about blurb under Website.
5. Metrics canvas reflects the latest `/api/v1/scrapers/report` totals.
6. Present the three tables above to the user.

## Do not

- Invent non-F&B merchants.
- Leave Wine Farms empty by omitting `WINE_FARM_PACK`, or tag grocery Casino
  chains as Wine Farms / Entertainment.
- Scrape only `NEW_MARKETS` / `only_new` when the user invokes `/scrape`.
- Delete marketing contacts on re-scrape (upsert / refresh only).
- Skip the results breakdown tables.
- Skip the website / metrics refresh after a successful scrape.
- Prefer stock/Unsplash placeholders when a real deal or landing-page photo
  exists on the merchant site.
- Skip force photo order (deal page → site landing → dish placeholder).
- Use one generic lunch photo for all fallbacks instead of dish-matched
  placeholders from `deal_placeholders.py`.
- Use the company logo as the main deal hero image.
- Commit or push unless the user asks.
