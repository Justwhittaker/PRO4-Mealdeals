import {
  LOCATION_COOKIE,
  LOCATION_SOURCE_COOKIE,
  locationCookieValue,
  parseLocationCookie,
  type GeoTarget,
  type LocationSource,
} from "@/lib/geo";

const MAX_AGE_SECONDS = 60 * 60 * 24 * 180; // 180 days

export function setLocationPreference(
  target: GeoTarget,
  source: LocationSource,
): void {
  if (typeof document === "undefined") return;
  const value = locationCookieValue(target);
  const base = `Path=/; Max-Age=${MAX_AGE_SECONDS}; SameSite=Lax`;
  document.cookie = `${LOCATION_COOKIE}=${encodeURIComponent(value)}; ${base}`;
  document.cookie = `${LOCATION_SOURCE_COOKIE}=${source}; ${base}`;
}

export function clearLocationPreference(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${LOCATION_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
  document.cookie = `${LOCATION_SOURCE_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function readLocationPreferenceFromDocument(): {
  target: GeoTarget | null;
  source: LocationSource | null;
} {
  if (typeof document === "undefined") {
    return { target: null, source: null };
  }
  const map = Object.fromEntries(
    document.cookie.split("; ").map((part) => {
      const [k, ...rest] = part.split("=");
      return [k, decodeURIComponent(rest.join("=") ?? "")];
    }),
  );
  const target = parseLocationCookie(map[LOCATION_COOKIE] ?? null);
  const source = (map[LOCATION_SOURCE_COOKIE] as LocationSource | undefined) ?? null;
  return { target, source };
}
