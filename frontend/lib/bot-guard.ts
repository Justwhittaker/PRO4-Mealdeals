import { isAdCrawler } from "@/lib/crawlers";
import { isKnownMarketCountry } from "@/lib/geo";

/**
 * First path segments that are real site routes, not country codes.
 * Kept local so the edge check does not import the SEO module.
 */
const RESERVED_ROOTS = new Set([
  "dashboard",
  "contact",
  "newsletter",
  "privacy",
  "cookies",
  "terms",
  "about",
  "guides",
  "go",
  "api",
  "admin",
  "sitemap",
  "sitemaps",
  "robots",
  "ads",
  "llms",
  "favicon",
  "icon",
  "apple-icon",
  "manifest",
  "live-metrics",
  "_next",
  "static",
]);

/**
 * Aggressive SEO scrapers and generic HTTP libraries. Search and social
 * crawlers are not listed here; those stay on the allow path in crawlers.ts.
 * Patterns are specific so a normal browser UA is not rejected.
 */
const JUNK_BOT =
  /\b(AhrefsBot|SemrushBot|MJ12bot|DotBot|PetalBot|Bytespider|BLEXBot|DataForSeoBot|SerpstatBot|SeekportBot|MegaIndex|ZoominfoBot|SEOkicks|Barkrowler|MauiBot|CensysInspect|InternetMeasurement|Nuclei|sqlmap|nikto|masscan|zgrab|HTTrack|python-requests|Scrapy|Go-http-client|libwww-perl|wget\/|curl\/)\b/i;

function isReservedSlug(slug: string): boolean {
  return RESERVED_ROOTS.has(slug.trim().toLowerCase());
}

/** City listings (`/us/new-york`) and deal pages (`/us/new-york/deals/{id}`). */
export function isDealOrCityPath(pathname: string): boolean {
  const parts = pathname.split("/").filter(Boolean);
  const isCity = parts.length === 2;
  const isDeal = parts.length === 4 && parts[2] === "deals" && Boolean(parts[3]);
  if (!isCity && !isDeal) return false;
  const country = parts[0] ?? "";
  const city = parts[1] ?? "";
  if (!country || !city) return false;
  if (country.includes(".") || city.includes(".")) return false;
  if (isReservedSlug(country) || isReservedSlug(city)) return false;
  return isKnownMarketCountry(country);
}

export function isJunkBot(userAgent: string | null | undefined): boolean {
  if (!userAgent?.trim()) return false;
  return JUNK_BOT.test(userAgent);
}

/**
 * True when middleware should return a tiny response and skip rendering.
 * Googlebot, Bingbot, and the other crawlers in `isAdCrawler` are never rejected.
 */
export function shouldCheapRejectBot(
  pathname: string,
  userAgent: string | null | undefined,
): boolean {
  if (!isDealOrCityPath(pathname)) return false;
  if (isAdCrawler(userAgent)) return false;
  return isJunkBot(userAgent);
}
