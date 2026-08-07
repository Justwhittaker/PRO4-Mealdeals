> Paste this entire document into Cursor Agent / Composer when working on the MealDeals `frontend/`.

---

# CURSOR INSTRUCTION: MealDeals Frontend (Next.js App Router)

## 1. Objective
Build and maintain the **MealDeals** merchant + public web app in `frontend/` using **Next.js 14+ App Router, TypeScript, Tailwind, shadcn-style UI**. Connect to the FastAPI backend at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

Do **not** rewrite the Django legacy app. Prefer extending existing files under `frontend/` over greenfield duplicates.

## 2. Product rules (must preserve)

### Public multi-region SEO
- `app/[country]/page.tsx` — country landing  
- `app/[country]/[city]/page.tsx` — city feed (auto-scraped deals from API)  
- `app/[country]/[city]/deals/[id]/page.tsx` — deal detail  
- `app/go/[deal_id]/route.ts` — 302 to backend `/go/{deal_id}`  
- Root `app/page.tsx` — geo banner via `x-vercel-ip-country` / `cf-ipcountry`

Country codes in URLs may be `uk`; API uses `GB` — map `UK → GB` in `lib/api.ts`.

### Feed ranking (client + server)
- Subscriber **Priority** deals rank above scraped external deals  
- Use `lib/priority.ts` for badges / client sort  
- Scraped = “External Deal”; paid = “Verified Direct Deal”

### Priority subscription (€20)
- Intro: **€20 for 3 months** → **3 deal slots**  
- Then: **€20 / month** → still **3 slots**  
- Stripe prices: `STRIPE_PRICE_PRIORITY_INTRO_EUR`, `STRIPE_PRICE_PRIORITY_MONTHLY_EUR`  
- Checkout via `actions/stripe.ts` → webhook syncs Postgres (`is_subscriber`, `tier_level=featured`, `deal_slot_limit=3`, `subscription_phase`)

### Design Special (€20 one-time) — separate from sub
- Buy box + form at `/dashboard/design`  
- Does **not** consume Priority’s 3 slots  
- Live for **~60 days** (`slot_exempt` deals)  
- Flow: brief + optional photo URLs → create design request → Stripe `mode: payment` → ops fulfills  
- Fulfill: `/dashboard/design/fulfill` or inbound email subject `DESIGN:{request-id}` → `/api/inbound/design-email`  
- Price env: `STRIPE_PRICE_DESIGN_SPECIAL_EUR`

### Merchant profile + deal history
- `/dashboard/profile` — venue identity (email, contact, bio, slot usage)  
- `/dashboard/deals` — history: **Archive** (deactivate / free slot), **Reactivate**, **Repost**  
- Login links email → Postgres profile via `lib/merchant-bootstrap.ts` (creates profile if missing)  
- Only **non–slot-exempt** active deals count toward the 3 Priority slots

## 3. Directory map (keep / extend)

```
frontend/
├── app/
│   ├── [country]/[city]/...
│   ├── (dashboard)/dashboard/
│   │   ├── page.tsx
│   │   ├── profile/
│   │   ├── deals/ (+ new/, deal-history)
│   │   ├── design/ (+ fulfill/)
│   │   └── billing/
│   ├── api/
│   │   ├── auth/[...nextauth]/
│   │   ├── webhooks/stripe/
│   │   └── inbound/design-email/
│   ├── go/[deal_id]/
│   └── page.tsx
├── components/ (ads, deals, geo, ui)
├── lib/ (api, auth, stripe, priority, currency, merchant-bootstrap)
└── actions/stripe.ts
```

## 4. API client (`lib/api.ts`)
- Always map snake_case ↔ UI models  
- Feed: `GET /api/v1/deals/feed?country_code&city&currency_override&…`  
- Profile: `GET/PATCH /api/v1/merchants/{id}/profile`  
- History: `GET /api/v1/merchants/{id}/deals/history`  
- Repost: `POST /api/v1/merchants/{id}/deals/{dealId}/repost`  
- Design: `POST /api/v1/design-requests`, mark-paid, fulfill  
- Graceful empty/error UI when API is down

## 5. Stripe webhook (`app/api/webhooks/stripe/route.ts`)
Branch on `metadata.plan`:
- `design_special` → `markDesignRequestPaid`  
- otherwise Priority subscription → update merchant + optional schedule intro→monthly  

## 6. Design / UX constraints
- Brand **Meal Deals** as hero-level on public landings (original PRO4 / Balsamiq)  
- Fonts: **Crimson Text** + **Oswald** (original README)  
- Visual: **white + dark burgundy** `rgb(197, 20, 20)` appetite red  
- Landing follows Balsamiq: hero image, dual search (restaurant + city), advert cover-flow carousel, social footer  
- Avoid purple gradients and broadsheet clichés  
- Cards OK for deal interactions; Groupon-style deal tiles  
- Mobile-first; AdSense in-feed every 5th item (`InFeedAd`)

## 7. Env (`.env.local`)
```
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=…
STRIPE_SECRET_KEY=sk_test_…
STRIPE_WEBHOOK_SECRET=whsec_…
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_…
STRIPE_PRICE_PRIORITY_INTRO_EUR=…
STRIPE_PRICE_PRIORITY_MONTHLY_EUR=…
STRIPE_PRICE_DESIGN_SPECIAL_EUR=…
DESIGN_FULFILL_SECRET=mealdeals-design
```

## 8. Acceptance checklist
1. Geo banner on `/`  
2. City feed loads / auto-scrapes via API  
3. Merchant login creates/links profile  
4. Priority billing checkout + webhook fields  
5. Deals history: archive / reactivate / repost respects 3 slots  
6. Design Special buy box → €20 payment → paid request listed  
7. Fulfill path posts slot-exempt 60-day deal  
8. `npm run build` passes  

## 9. Working style
- Small, focused diffs; match existing patterns  
- No unrelated refactors; no new markdown docs unless asked  
- TypeScript strict; no inline imports  
- Exhaustive `switch` defaults with `never` where using unions  

---
