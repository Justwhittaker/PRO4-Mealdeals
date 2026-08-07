import { MARKET_COUNTRIES } from "@/lib/markets-catalog";

export const LOCATION_COOKIE = "dineadeal_loc";
export const LOCATION_SOURCE_COOKIE = "dineadeal_loc_source";

export type LocationSource = "geo" | "search" | "manual";

export interface GeoTarget {
  countryCode: string;
  countryLabel: string;
  citySlug: string;
  cityLabel: string;
}

export interface CityOption {
  country: string;
  city: string;
  label: string;
  lat: number;
  lon: number;
  aliases?: string[];
}

/** Supported cities with centroids for nearest-match geo. */
export const CITY_CATALOG: CityOption[] = [
  {
    country: "uk",
    city: "london",
    label: "London",
    lat: 51.5074,
    lon: -0.1278,
    aliases: ["greater london"],
  },
  {
    country: "uk",
    city: "manchester",
    label: "Manchester",
    lat: 53.4808,
    lon: -2.2426,
  },
  {
    country: "uk",
    city: "birmingham",
    label: "Birmingham",
    lat: 52.4862,
    lon: -1.8904,
  },
  {
    country: "us",
    city: "new-york",
    label: "New York",
    lat: 40.7128,
    lon: -74.006,
    aliases: ["nyc", "new york city", "brooklyn", "manhattan"],
  },
  {
    country: "us",
    city: "los-angeles",
    label: "Los Angeles",
    lat: 34.0522,
    lon: -118.2437,
    aliases: ["la", "l.a."],
  },
  {
    country: "us",
    city: "chicago",
    label: "Chicago",
    lat: 41.8781,
    lon: -87.6298,
  },
  {
    country: "us",
    city: "miami",
    label: "Miami",
    lat: 25.7617,
    lon: -80.1918,
  },
  {
    country: "ie",
    city: "dublin",
    label: "Dublin",
    lat: 53.3498,
    lon: -6.2603,
  },
  {
    country: "au",
    city: "sydney",
    label: "Sydney",
    lat: -33.8688,
    lon: 151.2093,
  },
  {
    country: "au",
    city: "melbourne",
    label: "Melbourne",
    lat: -37.8136,
    lon: 144.9631,
  },
  {
    country: "ca",
    city: "toronto",
    label: "Toronto",
    lat: 43.6532,
    lon: -79.3832,
  },
  {
    country: "ca",
    city: "vancouver",
    label: "Vancouver",
    lat: 49.2827,
    lon: -123.1207,
  },
  {
    country: "nz",
    city: "auckland",
    label: "Auckland",
    lat: -36.8485,
    lon: 174.7633,
  },
  {
    country: "za",
    city: "cape-town",
    label: "Cape Town",
    lat: -33.9249,
    lon: 18.4241,
  },
];

/** Coords-backed cities for nearest-match geo (subset). Full markets: MARKET_COUNTRIES. */
const COORDS_BY_KEY = new Map(
  CITY_CATALOG.map((c) => [`${c.country}/${c.city}`, c] as const),
);

function marketCityToOption(city: {
  country: string;
  city: string;
  label: string;
}): CityOption {
  const known = COORDS_BY_KEY.get(`${city.country}/${city.city}`);
  return {
    country: city.country,
    city: city.city,
    label: city.label,
    lat: known?.lat ?? 0,
    lon: known?.lon ?? 0,
    aliases: known?.aliases,
  };
}

/** All scrape-market cities (91 countries) for country pages / search. */
export const POPULAR_CITIES = MARKET_COUNTRIES.flatMap((m) =>
  m.cities.map(({ country, city, label }) => ({ country, city, label })),
);

/** Map IP country codes → default local portal (country-level fallback). */
export const GEO_DEFAULTS: Record<string, GeoTarget> = Object.fromEntries(
  MARKET_COUNTRIES.flatMap((m) => {
    const hub = m.cities[0];
    if (!hub) return [];
    const target: GeoTarget = {
      countryCode: m.code,
      countryLabel: m.label,
      citySlug: hub.city,
      cityLabel: hub.label,
    };
    const entries: [string, GeoTarget][] = [[m.iso, target]];
    if (m.iso === "GB") entries.push(["UK", target]);
    return entries;
  }),
);

const COUNTRY_LABELS: Record<string, string> = Object.fromEntries(
  MARKET_COUNTRIES.flatMap((m) => {
    const label =
      m.code === "uk" || m.code === "us" ? `the ${m.label}` : m.label;
    const pairs: [string, string][] = [[m.code, label]];
    if (m.code === "uk") pairs.push(["gb", label]);
    return pairs;
  }),
);

/** Full country names for UI (no leading "the"). Keyed by route slug + ISO. */
const COUNTRY_SEARCH_LABELS: Record<string, string> = Object.fromEntries(
  MARKET_COUNTRIES.flatMap((m) => {
    const pairs: [string, string][] = [
      [m.code, m.label],
      [m.iso.toLowerCase(), m.label],
    ];
    if (m.code === "uk") pairs.push(["gb", m.label]);
    return pairs;
  }),
);

const CITY_SEARCH_LABELS: Record<string, string> = Object.fromEntries(
  MARKET_COUNTRIES.flatMap((m) =>
    m.cities.map((c) => [`${c.country}/${c.city}`, c.label] as const),
  ),
);

export interface CountryOption {
  code: string;
  label: string;
  cities: CityOption[];
}

/** All 91 scrape markets, each with nested cities. */
export function listCountries(): CountryOption[] {
  return MARKET_COUNTRIES.map((m) => ({
    code: m.code,
    label: m.label,
    cities: m.cities
      .map(marketCityToOption)
      .sort((a, b) => a.label.localeCompare(b.label)),
  })).sort((a, b) => a.label.localeCompare(b.label));
}

/** Full country name for breadcrumbs, headings, banners (never abbreviations). */
export function countrySearchLabel(code: string): string {
  const key = code.toLowerCase() === "gb" ? "uk" : code.toLowerCase();
  return COUNTRY_SEARCH_LABELS[key] ?? titleCaseSlug(key);
}

/** @deprecated Prefer countrySearchLabel — same full-name behaviour. */
export const countryDisplayLabel = countrySearchLabel;

/** Full city name from markets catalog when known. */
export function cityDisplayLabel(country: string, city: string): string {
  const countryKey =
    country.toLowerCase() === "gb" ? "uk" : country.toLowerCase();
  const cityKey = city.toLowerCase().replace(/\s+/g, "-");
  return (
    CITY_SEARCH_LABELS[`${countryKey}/${cityKey}`] ?? titleCaseSlug(cityKey)
  );
}

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function titleCaseSlug(slug: string): string {
  return slug
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function cityToTarget(option: CityOption): GeoTarget {
  return {
    countryCode: option.country,
    countryLabel: countrySearchLabel(option.country),
    citySlug: option.city,
    cityLabel: option.label,
  };
}

/** Resolve catalog centroid for radius feeds (lat/lon). */
export function lookupCityCoords(
  country: string,
  city: string,
): { lat: number; lon: number } | null {
  const countrySlug = country.toLowerCase() === "gb" ? "uk" : country.toLowerCase();
  const citySlug = city.toLowerCase().replace(/\s+/g, "-");
  const known = CITY_CATALOG.find(
    (c) => c.country === countrySlug && c.city === citySlug,
  );
  if (known) return { lat: known.lat, lon: known.lon };
  return null;
}

export function parseLocationCookie(
  value: string | undefined | null,
): GeoTarget | null {
  if (!value) return null;
  const [country, city] = value.toLowerCase().split("/");
  if (!country || !city) return null;
  const known = CITY_CATALOG.find(
    (c) => c.country === country && c.city === city,
  );
  if (known) return cityToTarget(known);
  return {
    countryCode: country === "gb" ? "uk" : country,
    countryLabel: countrySearchLabel(country),
    citySlug: city,
    cityLabel: cityDisplayLabel(country, city),
  };
}

export function locationCookieValue(target: GeoTarget): string {
  return `${target.countryCode}/${target.citySlug}`;
}

/** Haversine distance in km. */
export function distanceKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const r = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(a));
}

export function nearestCity(lat: number, lon: number): CityOption {
  let best = CITY_CATALOG[0]!;
  let bestDist = Number.POSITIVE_INFINITY;
  for (const city of CITY_CATALOG) {
    const d = distanceKm(lat, lon, city.lat, city.lon);
    if (d < bestDist) {
      bestDist = d;
      best = city;
    }
  }
  return best;
}

export function resolveGeoTarget(countryHeader: string | null): GeoTarget | null {
  if (!countryHeader) return null;
  return GEO_DEFAULTS[countryHeader.toUpperCase()] ?? null;
}

/**
 * Resolve visitor location from edge/IP headers.
 * Prefer city header when present (Vercel / Cloudflare).
 */
export function resolveGeoFromHeaders(headersList: {
  get(name: string): string | null;
}): GeoTarget | null {
  const countryRaw =
    headersList.get("x-vercel-ip-country") ??
    headersList.get("cf-ipcountry") ??
    headersList.get("x-country-code");
  if (!countryRaw || countryRaw.toUpperCase() === "XX") return null;

  const cityRaw =
    headersList.get("x-vercel-ip-city") ??
    headersList.get("cf-ipcity") ??
    headersList.get("x-city") ??
    headersList.get("x-vercel-ip-city-name");

  const countryKey = countryRaw.toUpperCase();
  const countrySlug =
    countryKey === "GB" || countryKey === "UK"
      ? "uk"
      : countryKey.toLowerCase();

  if (cityRaw) {
    const decoded = decodeURIComponent(cityRaw.replace(/\+/g, " "));
    const slug = slugify(decoded);
    const match = CITY_CATALOG.find(
      (c) =>
        c.country === countrySlug &&
        (c.city === slug ||
          c.label.toLowerCase() === decoded.toLowerCase() ||
          c.aliases?.some((a) => a === decoded.toLowerCase() || slugify(a) === slug)),
    );
    if (match) return cityToTarget(match);

    // Unknown city in a supported scrape market — still use that city slug
    if (GEO_DEFAULTS[countryKey] || COUNTRY_SEARCH_LABELS[countrySlug]) {
      return {
        countryCode: countrySlug,
        countryLabel: countrySearchLabel(countrySlug),
        citySlug: slug,
        cityLabel: cityDisplayLabel(countrySlug, slug),
      };
    }
  }

  return resolveGeoTarget(countryRaw);
}

/** Free-text city/country search → catalog match or best-effort slug. */
export function resolveLocationQuery(query: string): GeoTarget | null {
  const q = query.trim().toLowerCase();
  if (!q) return null;

  // Prefer exact country name / code hits first.
  for (const market of MARKET_COUNTRIES) {
    if (
      market.label.toLowerCase() === q ||
      market.code === q ||
      market.iso.toLowerCase() === q ||
      (market.code === "uk" && (q === "gb" || q === "britain" || q === "england"))
    ) {
      const hub = market.cities[0];
      if (!hub) continue;
      return cityToTarget(marketCityToOption(hub));
    }
  }

  const allCities = MARKET_COUNTRIES.flatMap((m) =>
    m.cities.map(marketCityToOption),
  );

  for (const city of allCities) {
    const hay = [
      city.label.toLowerCase(),
      city.city,
      city.country,
      ...(city.aliases ?? []),
      `${city.label.toLowerCase()} ${city.country}`,
      `${city.city} ${city.country}`,
    ];
    if (hay.some((h) => h === q || h.includes(q) || q.includes(h))) {
      return cityToTarget(city);
    }
  }

  // "new york usa" / "paris france" style
  const parts = q.split(/[,\s]+/).filter(Boolean);
  if (parts.length >= 2) {
    const maybeCountry = parts[parts.length - 1]!;
    const countryMap: Record<string, string> = Object.fromEntries(
      MARKET_COUNTRIES.flatMap((m) => {
        const entries: [string, string][] = [
          [m.code, m.code],
          [m.iso.toLowerCase(), m.code],
          [m.label.toLowerCase(), m.code],
          [slugify(m.label), m.code],
        ];
        if (m.code === "uk") {
          entries.push(["britain", "uk"], ["england", "uk"]);
        }
        if (m.code === "us") entries.push(["usa", "us"]);
        return entries;
      }),
    );
    const country = countryMap[maybeCountry] ?? countryMap[slugify(maybeCountry)];
    if (country) {
      const cityPart = parts.slice(0, -1).join(" ");
      const slug = slugify(cityPart);
      const known = allCities.find(
        (c) =>
          c.country === country &&
          (c.city === slug || c.label.toLowerCase() === cityPart),
      );
      if (known) return cityToTarget(known);
      return {
        countryCode: country,
        countryLabel: countrySearchLabel(country),
        citySlug: slug,
        cityLabel: cityDisplayLabel(country, slug),
      };
    }
  }

  return null;
}

/** Last-resort when IP/browser geo unavailable (dev without headers). */
export function defaultGeoTarget(): GeoTarget {
  return GEO_DEFAULTS.GB!;
}
