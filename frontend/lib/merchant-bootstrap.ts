/**
 * Ensure a Postgres merchant profile exists for a login email.
 * Creates a default London venue if none is linked yet.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function resolveLondonLocationId(): Promise<string | null> {
  const list = await fetch(
    `${API_URL}/api/v1/geo/locations?country_code=GB&city=London&limit=1`,
    { cache: "no-store" },
  );
  if (list.ok) {
    const rows = (await list.json()) as { id: string }[];
    if (rows[0]?.id) return rows[0].id;
  }

  const locRes = await fetch(`${API_URL}/api/v1/geo/locations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      country_code: "GB",
      city: "London",
      timezone: "Europe/London",
      latitude: 51.5074,
      longitude: -0.1278,
    }),
    cache: "no-store",
  });
  if (!locRes.ok) return null;
  const loc = (await locRes.json()) as { id: string };
  return loc.id;
}

export async function resolveMerchantIdForEmail(
  email: string,
): Promise<string | null> {
  const normalized = email.trim().toLowerCase();
  if (!normalized) return null;

  try {
    const existing = await fetch(
      `${API_URL}/api/v1/merchants/by-email/${encodeURIComponent(normalized)}`,
      { cache: "no-store" },
    );
    if (existing.ok) {
      const profile = (await existing.json()) as { id: string };
      return profile.id;
    }

    const locationId = await resolveLondonLocationId();
    if (!locationId) return null;

    const createRes = await fetch(`${API_URL}/api/v1/merchants`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: normalized.split("@")[0] || "My Venue",
        category: "bistro",
        location_id: locationId,
        email: normalized,
        contact_name: normalized.split("@")[0],
        is_subscriber: false,
        tier_level: "free",
        deal_slot_limit: 0,
        subscription_phase: "none",
      }),
      cache: "no-store",
    });

    if (!createRes.ok) return null;
    const merchant = (await createRes.json()) as { id: string };
    return merchant.id;
  } catch {
    return null;
  }
}
