import type { FeedParams } from "@/lib/api";
import type { ParentCategoryId } from "@/lib/categories";
import { lookupCityCoords } from "@/lib/geo";
import type { FeedSort, RadiusMiles } from "@/lib/radius";

/** Ranked page size for country/city listings — keep under API MAX_FEED_LIMIT. */
export const GEO_FEED_PAGE_SIZE = 200;

export type DealFeedScope = "country" | "city";

export interface BuildDealFeedParamsInput {
  scope: DealFeedScope;
  country: string;
  city?: string;
  currency?: string;
  sort?: FeedSort;
  radius?: RadiusMiles;
  category?: ParentCategoryId | "all";
  page?: number;
  limit?: number;
}

/** 1-based page from `?page=` (invalid / missing → 1). */
export function parseFeedPage(raw?: string | string[] | null): number {
  const value = Array.isArray(raw) ? raw[0] : raw;
  const n = Number.parseInt(String(value ?? "1"), 10);
  if (!Number.isFinite(n) || n < 1) return 1;
  return n;
}

export function feedPageOffset(page: number, pageSize = GEO_FEED_PAGE_SIZE): number {
  return Math.max(0, (page - 1) * pageSize);
}

/**
 * Build API feed params by page scope.
 * - country: whole country (no city / radius)
 * - city: that city — exact name match, plus optional radius around the
 *   catalog centroid so "Featured / Nearest" and mile filters work without
 *   leaking the rest of the country
 */
export function buildDealFeedParams(
  input: BuildDealFeedParamsInput,
): FeedParams {
  const limit = input.limit ?? GEO_FEED_PAGE_SIZE;
  const page = input.page && input.page > 0 ? input.page : 1;
  const base: FeedParams = {
    country: input.country,
    currency: input.currency,
    sort: input.sort ?? "score",
    limit,
    offset: feedPageOffset(page, limit),
  };

  if (input.category && input.category !== "all") {
    base.category = input.category;
  }

  if (input.scope === "country" || !input.city) {
    return base;
  }

  const city = input.city;
  const coords = lookupCityCoords(input.country, city);

  if (coords && coords.lat !== 0 && coords.lon !== 0) {
    return {
      ...base,
      city,
      lat: coords.lat,
      lon: coords.lon,
      radiusMiles: input.radius,
    };
  }

  return {
    ...base,
    city,
  };
}

export function feedEmptyMessage(
  scope: DealFeedScope,
  placeLabel: string,
): { emptyMessage: string; emptyHint: string } {
  if (scope === "city") {
    return {
      emptyMessage: `No deals near ${placeLabel} yet.`,
      emptyHint: "Widen the radius or try another city.",
    };
  }
  return {
    emptyMessage: `No deals listed across ${placeLabel} yet.`,
    emptyHint: "Search another country or check back soon.",
  };
}
