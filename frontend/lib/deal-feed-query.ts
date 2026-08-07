import type { FeedParams } from "@/lib/api";
import { lookupCityCoords } from "@/lib/geo";
import type { FeedSort, RadiusMiles } from "@/lib/radius";

const GEO_FEED_LIMIT = 10000;

export type DealFeedScope = "country" | "city";

export interface BuildDealFeedParamsInput {
  scope: DealFeedScope;
  country: string;
  city?: string;
  currency?: string;
  sort?: FeedSort;
  radius?: RadiusMiles;
  limit?: number;
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
  const limit = input.limit ?? GEO_FEED_LIMIT;
  const base: FeedParams = {
    country: input.country,
    currency: input.currency,
    sort: input.sort ?? "score",
    limit,
  };

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
