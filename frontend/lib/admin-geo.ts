import { slugifyCity } from "@/lib/area-label";

/** ISO or route slug → URL country segment (GB → uk). */
export function routeCountrySlug(countryCode: string): string {
  const code = countryCode.trim().toLowerCase();
  if (code === "gb") return "uk";
  return code;
}

export function countryDisplayName(countryCode: string): string {
  const iso = countryCode.trim().toUpperCase();
  if (!iso || iso === "(UNKNOWN)") return "Unknown";
  try {
    const dn = new Intl.DisplayNames(["en"], { type: "region" });
    return dn.of(iso) || iso;
  } catch {
    return iso;
  }
}

export function cityDisplayName(city: string): string {
  const value = city.trim();
  if (!value || value === "(unknown)") return "Unknown";
  return value
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

export function publicCityPath(countryCode: string, city: string): string {
  return `/${routeCountrySlug(countryCode)}/${slugifyCity(city)}`;
}

export function publicDealPath(
  countryCode: string,
  city: string,
  dealId: string,
): string {
  return `${publicCityPath(countryCode, city)}/deals/${dealId}`;
}

export type GeoKeyedRow = {
  countryCode: string;
  city: string;
};

export type GeoCityGroup<T> = {
  city: string;
  items: T[];
};

export type GeoCountryGroup<T> = {
  countryCode: string;
  cities: GeoCityGroup<T>[];
  total: number;
};

/** Sort country → city groups; items within a city keep caller order. */
export function groupByCountryCity<T extends GeoKeyedRow>(
  rows: T[],
): GeoCountryGroup<T>[] {
  const countries = new Map<string, Map<string, T[]>>();

  for (const row of rows) {
    const country = row.countryCode?.trim() || "(unknown)";
    const city = row.city?.trim() || "(unknown)";
    let cities = countries.get(country);
    if (!cities) {
      cities = new Map();
      countries.set(country, cities);
    }
    const bucket = cities.get(city);
    if (bucket) bucket.push(row);
    else cities.set(city, [row]);
  }

  return Array.from(countries.entries())
    .map(([countryCode, cityMap]) => {
      const cities = Array.from(cityMap.entries())
        .map(([city, items]) => ({ city, items }))
        .sort((a, b) =>
          cityDisplayName(a.city).localeCompare(cityDisplayName(b.city)),
        );
      const total = cities.reduce((sum, c) => sum + c.items.length, 0);
      return { countryCode, cities, total };
    })
    .sort((a, b) =>
      countryDisplayName(a.countryCode).localeCompare(
        countryDisplayName(b.countryCode),
      ),
    );
}

export function shareLabel(count: number, total: number): string {
  if (total <= 0) return "0%";
  return `${((count / total) * 100).toFixed(1)}%`;
}
