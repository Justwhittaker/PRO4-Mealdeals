# MealDeals Frontend

Next.js 14 (App Router) multi-region meal deals platform with merchant billing, AdSense slots, and geo-aware routing.

## Stack

- Next.js 14 + TypeScript (strict) + Tailwind CSS
- shadcn-style UI primitives (Button, Card, Badge, Input, Select, Label)
- NextAuth (credentials stub + optional Google)
- Stripe Checkout + Customer Portal + webhooks
- Google AdSense (InFeed + sticky sidebar)

## Design

Warm charcoal + citrus lime. Display font: Fraunces. Body: DM Sans.

## Setup

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Point `NEXT_PUBLIC_API_URL` at the backend (default `http://localhost:8000`).

## Key routes

| Route | Purpose |
| --- | --- |
| `/` | Geo banner + brand hero |
| `/[country]` | Country landing + feed |
| `/[country]/[city]` | City feed (ranked) |
| `/[country]/[city]/deals/[id]` | Deal detail + value calc |
| `/go/[deal_id]` | Redirect to backend `/go/{id}` |
| `/dashboard` | Merchant portal (auth) |
| `/dashboard/deals/new` | Create deal + live value calculator |
| `/dashboard/billing` | Stripe tiers + Customer Portal |
| `/api/webhooks/stripe` | Subscription lifecycle |

## Env vars

See `.env.example` for NextAuth, Stripe price IDs, AdSense client, and API URL.

## Feed ranking

`lib/priority.ts`:

`Score = Tier Weight + Proximity + Freshness − Scrape Penalty`

- Enterprise +1000, Featured +500, Scraped 0
- Distance decays from +100
- Subscribers get **Verified Direct Deal**; scraped get **External Deal**

## Scripts

```bash
npm run dev      # local development
npm run build    # production build
npm run start    # serve build
npm run lint     # eslint
```
