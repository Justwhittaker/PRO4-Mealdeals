import type { Metadata } from "next";
import type { Deal } from "@/lib/api";
import { BRAND_NAME, BRAND_SITE_URL } from "@/lib/brand";
import {
  cityDisplayLabel,
  countrySearchLabel,
  isKnownMarketCountry,
  listCountries,
  normalizeCountrySlug,
} from "@/lib/geo";

export const HOME_DESCRIPTION =
  "Find dining deals near you across cities worldwide. Restaurants advertise on a flat-rate platform — no voucher cut.";

const RESERVED_GEO_SLUGS = new Set([
  "dashboard",
  "contact",
  "newsletter",
  "privacy",
  "cookies",
  "terms",
  "about",
  "go",
  "api",
  "admin",
  "sitemap",
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

export function absoluteUrl(path = "/"): string {
  const base = BRAND_SITE_URL.replace(/\/$/, "");
  if (!path || path === "/") return `${base}/`;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

export function listingPath(
  country: string,
  city?: string,
  dealId?: string,
): string {
  const countrySlug = normalizeCountrySlug(country);
  if (!city) return `/${countrySlug}`;
  const citySlug = city.toLowerCase().replace(/\s+/g, "-");
  if (!dealId) return `/${countrySlug}/${citySlug}`;
  return `/${countrySlug}/${citySlug}/deals/${dealId}`;
}

/** File-like or reserved first segments that must not become country pages. */
export function isReservedGeoSlug(slug: string): boolean {
  const raw = slug.trim().toLowerCase();
  if (!raw) return true;
  if (raw.includes(".") || raw.includes("%") || raw.includes("/")) return true;
  const stem = raw.replace(/\.(xml|txt|html|ico|json|js|css)$/i, "");
  return RESERVED_GEO_SLUGS.has(raw) || RESERVED_GEO_SLUGS.has(stem);
}

export function isIndexableCountrySlug(slug: string): boolean {
  if (isReservedGeoSlug(slug)) return false;
  return isKnownMarketCountry(slug);
}

export function isIndexableCitySlug(country: string, city: string): boolean {
  if (!isIndexableCountrySlug(country)) return false;
  if (isReservedGeoSlug(city)) return false;
  return true;
}

export function publicPageMetadata(opts: {
  title: string | { absolute: string };
  description: string;
  path: string;
  image?: string | null;
  index?: boolean;
}): Metadata {
  const url = absoluteUrl(opts.path);
  const fullTitle =
    typeof opts.title === "string"
      ? `${opts.title} · ${BRAND_NAME}`
      : opts.title.absolute;
  const index = opts.index ?? true;
  const image = opts.image?.trim() || undefined;

  return {
    title: opts.title,
    description: opts.description,
    alternates: { canonical: url },
    robots: index
      ? { index: true, follow: true }
      : { index: false, follow: false },
    openGraph: {
      type: "website",
      siteName: BRAND_NAME,
      locale: "en_GB",
      title: fullTitle,
      description: opts.description,
      url,
      ...(image ? { images: [{ url: image }] } : {}),
    },
    twitter: {
      card: image ? "summary_large_image" : "summary",
      title: fullTitle,
      description: opts.description,
      ...(image ? { images: [image] } : {}),
    },
  };
}

export function countryListingMetadata(country: string): Metadata {
  const label = countrySearchLabel(country);
  return publicPageMetadata({
    title: `Dining deals across ${label}`,
    description: `Compare lunch deals, early-bird menus, and hotel dining offers across ${label}. Venues advertise on a flat-rate platform — no voucher cut.`,
    path: listingPath(country),
  });
}

export function cityListingMetadata(country: string, city: string): Metadata {
  const countryLabel = countrySearchLabel(country);
  const cityLabel = cityDisplayLabel(country, city);
  return publicPageMetadata({
    title: `Lunch deals in ${cityLabel}`,
    description: `Dining deals in ${cityLabel}, ${countryLabel}. Lunch sets, early-bird menus, hotel packages, and drinks promotions — compare this week's offers without buying a voucher.`,
    path: listingPath(country, city),
  });
}

export function dealListingMetadata(
  deal: Deal,
  country: string,
  city: string,
): Metadata {
  const cityLabel = cityDisplayLabel(country, city);
  const description =
    deal.description?.replace(/\s+/g, " ").trim().slice(0, 160) ||
    `${deal.title} at ${deal.restaurantName} in ${cityLabel}. Flat-rate dining listing on ${BRAND_NAME}.`;
  return publicPageMetadata({
    title: deal.title,
    description,
    path: listingPath(deal.country || country, deal.city || city, deal.id),
    image: deal.imageUrl,
  });
}

export function websiteJsonLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: BRAND_NAME,
    url: absoluteUrl("/"),
    description: HOME_DESCRIPTION,
    publisher: {
      "@type": "Organization",
      name: BRAND_NAME,
      url: absoluteUrl("/"),
    },
  };
}

export function breadcrumbJsonLd(
  crumbs: { name: string; path: string }[],
): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: crumbs.map((crumb, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: crumb.name,
      item: absoluteUrl(crumb.path),
    })),
  };
}

export function itemListJsonLd(
  name: string,
  deals: Array<{ id: string; title: string; country: string; city: string }>,
): Record<string, unknown> {
  const items = deals.slice(0, 20);
  return {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name,
    numberOfItems: deals.length,
    itemListElement: items.map((deal, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: deal.title,
      url: absoluteUrl(listingPath(deal.country, deal.city, deal.id)),
    })),
  };
}

export function offerJsonLd(
  deal: Deal,
  country: string,
  city: string,
): Record<string, unknown> {
  const url = absoluteUrl(
    listingPath(deal.country || country, deal.city || city, deal.id),
  );
  const offer: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Offer",
    name: deal.title,
    url,
    seller: {
      "@type": "Restaurant",
      name: deal.restaurantName,
    },
    areaServed: cityDisplayLabel(country, city),
  };
  if (deal.description) offer.description = deal.description;
  if (deal.imageUrl) offer.image = deal.imageUrl;
  if (deal.price > 0) {
    offer.price = deal.price;
    offer.priceCurrency = deal.currency;
  }
  return offer;
}

export function sitemapStaticPaths(): string[] {
  return [
    "/",
    "/about",
    "/contact",
    "/newsletter",
    "/privacy",
    "/privacy/choices",
    "/privacy/partners",
    "/cookies",
    "/terms",
  ];
}

export function sitemapLocationPaths(): string[] {
  const paths: string[] = [];
  for (const country of listCountries()) {
    paths.push(listingPath(country.code));
    for (const city of country.cities) {
      paths.push(listingPath(country.code, city.city));
    }
  }
  return paths;
}

