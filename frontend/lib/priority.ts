export type TierLevel = "free" | "featured" | "enterprise" | "scraped";

export interface RankableDeal {
  id: string;
  tier: TierLevel;
  isSubscriber?: boolean;
  distanceKm?: number | null;
  createdAt: string | Date;
  isScraped?: boolean;
}

const TIER_WEIGHT: Record<TierLevel, number> = {
  enterprise: 1000,
  featured: 500,
  free: 50,
  scraped: 0,
};

const DISTANCE_MAX = 100;
const FRESHNESS_MAX = 80;
const FRESHNESS_HALF_LIFE_HOURS = 72;
const SCRAPE_PENALTY = 120;

/**
 * Score = Base Tier Weight + Location Proximity Weight + Freshness Weight - Scrape Penalty
 */
export function computePriorityScore(deal: RankableDeal): number {
  const tier: TierLevel =
    deal.isScraped || deal.tier === "scraped" ? "scraped" : deal.tier;

  const base = TIER_WEIGHT[tier] ?? 0;

  const distanceKm =
    typeof deal.distanceKm === "number" && Number.isFinite(deal.distanceKm)
      ? Math.max(0, deal.distanceKm)
      : null;

  // Decays from DISTANCE_MAX at 0km toward 0 at ~50km+
  const proximity =
    distanceKm === null
      ? DISTANCE_MAX * 0.4
      : DISTANCE_MAX * Math.exp(-distanceKm / 25);

  const created =
    deal.createdAt instanceof Date
      ? deal.createdAt
      : new Date(deal.createdAt);
  const ageHours = Math.max(
    0,
    (Date.now() - created.getTime()) / (1000 * 60 * 60),
  );
  const freshness =
    FRESHNESS_MAX *
    Math.exp((-Math.LN2 * ageHours) / FRESHNESS_HALF_LIFE_HOURS);

  const scrapePenalty =
    tier === "scraped" || deal.isScraped ? SCRAPE_PENALTY : 0;

  return base + proximity + freshness - scrapePenalty;
}

export function rankDeals<T extends RankableDeal>(deals: T[]): T[] {
  return [...deals].sort(
    (a, b) => computePriorityScore(b) - computePriorityScore(a),
  );
}

/** Featured / Priority / verified subscriber deals — always pin above the rest. */
export function isFeaturedDeal(deal: RankableDeal): boolean {
  if (deal.isScraped || deal.tier === "scraped") return false;
  return Boolean(
    deal.isSubscriber || deal.tier === "featured" || deal.tier === "enterprise",
  );
}

/** Fisher–Yates shuffle (mutates and returns the same array). */
function shuffleInPlace<T>(items: T[]): T[] {
  for (let i = items.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = items[i]!;
    items[i] = items[j]!;
    items[j] = tmp;
  }
  return items;
}

function businessKey(deal: { restaurantName?: string }): string {
  return (deal.restaurantName ?? "").trim().toLowerCase() || "_unknown";
}

/**
 * Match widest deal grid (`2xl:grid-cols-6`). Keeping the same business out of
 * the previous N cards means it won't land on the next row (same column or
 * beside it) on 2–6 column layouts.
 */
const GRID_SPREAD_GAP = 6;

function recentBusinessKeys<T extends { restaurantName?: string }>(
  placed: T[],
  gap: number,
): Set<string> {
  const keys = new Set<string>();
  const start = Math.max(0, placed.length - gap);
  for (let i = start; i < placed.length; i += 1) {
    keys.add(businessKey(placed[i]!));
  }
  return keys;
}

function pickWeightedKey(keys: string[], weights: number[]): string {
  const total = weights.reduce((sum, w) => sum + w, 0);
  if (total <= 0) return keys[Math.floor(Math.random() * keys.length)]!;
  let roll = Math.random() * total;
  for (let i = 0; i < keys.length; i += 1) {
    roll -= weights[i]!;
    if (roll <= 0) return keys[i]!;
  }
  return keys[keys.length - 1]!;
}

/**
 * Spread listings so the same business is not near itself in the grid —
 * including the next row — when other businesses are available.
 * Picks randomly among valid candidates (weighted by remaining count).
 */
export function spreadDealsByBusiness<
  T extends { restaurantName?: string },
>(deals: T[], minGap: number = GRID_SPREAD_GAP): T[] {
  if (deals.length <= 1) return [...deals];

  const buckets = new Map<string, T[]>();
  for (const deal of deals) {
    const key = businessKey(deal);
    const list = buckets.get(key) ?? [];
    list.push(deal);
    buckets.set(key, list);
  }
  for (const list of Array.from(buckets.values())) {
    shuffleInPlace(list);
  }

  const remaining = new Map<string, T[]>(buckets);
  const out: T[] = [];
  const lastIndex = new Map<string, number>();

  while (out.length < deals.length) {
    const blocked = recentBusinessKeys(out, minGap);
    const candidates: string[] = [];
    const weights: number[] = [];

    for (const [key, list] of Array.from(remaining.entries())) {
      if (list.length === 0) continue;
      if (blocked.has(key)) continue;
      candidates.push(key);
      // Prefer denser chains early (so they get spaced), with randomness.
      weights.push(list.length * 2 + Math.random());
    }

    let chosenKey: string | null =
      candidates.length > 0 ? pickWeightedKey(candidates, weights) : null;

    if (!chosenKey) {
      // Window is full of needed chains — pick the one unseen the longest.
      let bestDist = -1;
      const tied: string[] = [];
      for (const [key, list] of Array.from(remaining.entries())) {
        if (list.length === 0) continue;
        const prev = lastIndex.has(key) ? lastIndex.get(key)! : -minGap * 2;
        const dist = out.length - prev;
        if (dist > bestDist) {
          bestDist = dist;
          tied.length = 0;
          tied.push(key);
        } else if (dist === bestDist) {
          tied.push(key);
        }
      }
      if (tied.length === 0) break;
      chosenKey = tied[Math.floor(Math.random() * tied.length)]!;
    }

    const pile = remaining.get(chosenKey)!;
    out.push(pile.shift()!);
    lastIndex.set(chosenKey, out.length - 1);
    if (pile.length === 0) remaining.delete(chosenKey);
  }

  return out;
}

/**
 * Area listing order: featured / Priority deals always first (score-ranked),
 * then all other deals spread so duplicate businesses are not adjacent when
 * other merchants exist to interleave.
 * If the area has no Priority subs, return the spread scraped list only.
 */
export function areaListingDeals<
  T extends RankableDeal & { restaurantName?: string },
>(deals: T[]): T[] {
  const ranked = rankDeals(deals);
  const featured = ranked.filter(isFeaturedDeal);
  const rest = spreadDealsByBusiness(
    ranked.filter((d) => !isFeaturedDeal(d)),
  );
  if (featured.length === 0) return rest;
  return [...featured, ...rest];
}

export function dealBadge(deal: RankableDeal): {
  label: string;
  variant: "verified" | "featured";
} | null {
  // Scraped listings: no banner. Subscriber deals keep Verified.
  if (deal.isScraped || deal.tier === "scraped") {
    return null;
  }
  if (deal.isSubscriber || deal.tier === "featured" || deal.tier === "enterprise") {
    return { label: "Verified Deal", variant: "verified" };
  }
  return { label: "Featured", variant: "featured" };
}
