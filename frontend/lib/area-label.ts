/** Nested hub–town labels for scraped deals (e.g. Galway - Tuam). */

export function formatAreaLabel(
  hub?: string | null,
  local?: string | null,
): string | null {
  const hubName = (hub || "").trim().replace(/-/g, " ");
  if (!hubName) return null;
  const localName = (local || "").trim().replace(/-/g, " ");
  if (!localName) return hubName;
  if (localName.toLowerCase() === hubName.toLowerCase()) return hubName;
  if (localName.toLowerCase() === `${hubName.toLowerCase()} city`) return hubName;
  return `${hubName} - ${localName}`;
}

export function slugifyCity(city: string): string {
  return city.trim().toLowerCase().replace(/\s+/g, "-");
}
