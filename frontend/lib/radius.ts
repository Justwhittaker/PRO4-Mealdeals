/** Search radius options (miles) for geo deal feeds. */
export const RADIUS_OPTIONS = [25, 50, 100, 150] as const;

export type RadiusMiles = (typeof RADIUS_OPTIONS)[number];

export const DEFAULT_RADIUS_MILES: RadiusMiles = 25;

export function milesToKm(miles: number): number {
  return miles * 1.60934;
}

export function kmToMiles(km: number): number {
  return km / 1.60934;
}

export function parseRadiusMiles(
  value: string | undefined | null,
): RadiusMiles {
  const n = Number(value);
  if (RADIUS_OPTIONS.includes(n as RadiusMiles)) {
    return n as RadiusMiles;
  }
  return DEFAULT_RADIUS_MILES;
}

export function formatDistanceMiles(distanceKm: number | null | undefined): string | null {
  if (distanceKm == null || !Number.isFinite(distanceKm)) return null;
  const miles = kmToMiles(distanceKm);
  if (miles < 1) return "< 1 mi";
  return `${miles.toFixed(miles < 10 ? 1 : 0)} mi`;
}

export type FeedSort = "score" | "distance";

export function parseFeedSort(value: string | undefined | null): FeedSort {
  return value === "distance" ? "distance" : "score";
}
