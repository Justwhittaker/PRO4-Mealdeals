/** Next.js fetch cache tags — invalidated after scrapes via /api/revalidate. */

export const DEALS_TAG = "deals";

export function cityDealsTag(country: string, city: string): string {
  const raw = country.trim().toLowerCase();
  const cc = raw === "gb" ? "uk" : raw;
  const slug = city.trim().toLowerCase().replace(/\s+/g, "-");
  return `deals-${cc}-${slug}`;
}

export function dealTag(id: string): string {
  return `deal-${id}`;
}
