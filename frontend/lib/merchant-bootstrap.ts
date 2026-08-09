/**
 * Ensure a Postgres merchant profile exists for a login email.
 * Creates a default London venue if none is linked yet.
 *
 * Server-side auth must use a reachable API URL (Vercel → public API),
 * not localhost. Prefer API_URL, then NEXT_PUBLIC_API_URL.
 */

import { createHash } from "crypto";
import { TERMS_VERSION } from "@/lib/legal-config";

const API_URL = (
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000"
).replace(/\/$/, "");

export type MerchantTermsAcceptanceInput = {
  termsVersion?: string;
  acceptanceSource?: string;
  acceptedByEmail?: string;
  acceptedByName?: string;
  acceptedByUserId?: string;
};

function offlineMerchantId(email: string): string {
  const digest = createHash("sha256").update(email).digest("hex").slice(0, 32);
  // Valid-looking UUID shape for session.user.id consumers
  return [
    digest.slice(0, 8),
    digest.slice(8, 12),
    "4" + digest.slice(13, 16),
    "a" + digest.slice(17, 20),
    digest.slice(20, 32),
  ].join("-");
}

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

async function recordTermsAcceptance(
  merchantId: string,
  email: string,
  acceptance: MerchantTermsAcceptanceInput,
): Promise<void> {
  const contactName = acceptance.acceptedByName || email.split("@")[0] || null;
  await fetch(`${API_URL}/api/v1/merchants/${merchantId}/terms-acceptance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      terms_version: acceptance.termsVersion || TERMS_VERSION,
      acceptance_source:
        acceptance.acceptanceSource || "merchant_registration",
      accepted_by_email: acceptance.acceptedByEmail || email,
      accepted_by_name: contactName,
      accepted_by_user_id: acceptance.acceptedByUserId || merchantId,
    }),
    cache: "no-store",
  }).catch(() => {
    /* offline / API error — registration still proceeds */
  });
}

export async function resolveMerchantIdForEmail(
  email: string,
  options?: {
    /** When true, persist Terms acceptance for newly created (or first) profiles. */
    termsAccepted?: boolean;
    termsAcceptance?: MerchantTermsAcceptanceInput;
  },
): Promise<string | null> {
  const normalized = email.trim().toLowerCase();
  if (!normalized) return null;

  const acceptance = options?.termsAccepted
    ? {
        termsVersion: options.termsAcceptance?.termsVersion || TERMS_VERSION,
        acceptanceSource:
          options.termsAcceptance?.acceptanceSource ||
          "merchant_registration",
        acceptedByEmail:
          options.termsAcceptance?.acceptedByEmail || normalized,
        acceptedByName:
          options.termsAcceptance?.acceptedByName ||
          normalized.split("@")[0],
        acceptedByUserId: options.termsAcceptance?.acceptedByUserId,
      }
    : null;

  try {
    const existing = await fetch(
      `${API_URL}/api/v1/merchants/by-email/${encodeURIComponent(normalized)}`,
      { cache: "no-store" },
    );
    if (existing.ok) {
      const profile = (await existing.json()) as { id: string };
      // Existing account signing in — do not re-require Terms here.
      return profile.id;
    }

    const locationId = await resolveLondonLocationId();
    if (!locationId) {
      // API up enough to answer, but geo seed failed — still allow sign-in.
      return offlineMerchantId(normalized);
    }

    const createBody: Record<string, unknown> = {
      name: normalized.split("@")[0] || "My Venue",
      category: "bistro",
      location_id: locationId,
      email: normalized,
      contact_name: normalized.split("@")[0],
      is_subscriber: false,
      tier_level: "free",
      deal_slot_limit: 0,
      subscription_phase: "none",
    };

    if (acceptance) {
      createBody.terms_acceptance = {
        terms_version: acceptance.termsVersion,
        acceptance_source: acceptance.acceptanceSource,
        accepted_by_email: acceptance.acceptedByEmail,
        accepted_by_name: acceptance.acceptedByName,
        accepted_by_user_id: acceptance.acceptedByUserId,
      };
    }

    const createRes = await fetch(`${API_URL}/api/v1/merchants`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(createBody),
      cache: "no-store",
    });

    if (createRes.ok) {
      const merchant = (await createRes.json()) as { id: string };
      return merchant.id;
    }

    // Race: another request created the profile — fetch again and optionally record.
    const again = await fetch(
      `${API_URL}/api/v1/merchants/by-email/${encodeURIComponent(normalized)}`,
      { cache: "no-store" },
    );
    if (again.ok) {
      const profile = (await again.json()) as { id: string };
      if (acceptance) {
        await recordTermsAcceptance(profile.id, normalized, acceptance);
      }
      return profile.id;
    }

    return offlineMerchantId(normalized);
  } catch {
    // Tunnel/API unreachable from Vercel — allow credentials demo login.
    return offlineMerchantId(normalized);
  }
}
