import type { ApiResult } from "@/lib/api";

const API_URL =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

function adminKey(): string {
  return (process.env.ADMIN_API_KEY || "").trim();
}

async function adminFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiResult<T>> {
  const key = adminKey();
  if (!key) {
    return {
      ok: false,
      error: "ADMIN_API_KEY is not configured on the frontend server",
      status: 503,
    };
  }

  try {
    const res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-Admin-Key": key,
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });

    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = (await res.json()) as { detail?: string };
        if (typeof body.detail === "string") detail = body.detail;
      } catch {
        // keep statusText
      }
      return { ok: false, error: detail || `API ${res.status}`, status: res.status };
    }

    if (res.status === 204) {
      return { ok: true, data: undefined as T };
    }

    const text = await res.text();
    if (!text) return { ok: true, data: undefined as T };
    return { ok: true, data: JSON.parse(text) as T };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : "Admin API unreachable",
    };
  }
}

export type AdminMerchant = {
  id: string;
  name: string;
  email?: string | null;
  category: string;
  is_subscriber: boolean;
  tier_level: string;
  deal_slot_limit: number;
  subscription_phase: string;
  contact_name?: string | null;
  phone?: string | null;
  website?: string | null;
  bio?: string | null;
  logo_url?: string | null;
  location_id: string;
  location?: {
    id: string;
    country_code: string;
    city: string;
  } | null;
  created_at?: string;
  active_deal_count?: number;
  total_deal_count?: number;
  open_slots?: number;
};

export type AdminDeal = {
  id: string;
  merchant_id: string;
  is_active: boolean;
  deal_price: string | number;
  original_price: string | number;
  currency_code: string;
  image_url?: string | null;
  venue_category?: string | null;
  slot_exempt?: boolean;
  created_at: string;
  translations?: { title: string; description: string; language_code?: string }[];
};

export async function adminListMerchants(q?: string, limit = 5000) {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (q?.trim()) qs.set("q", q.trim());
  return adminFetch<{ count: number; results: AdminMerchant[] }>(
    `/api/v1/admin/merchants?${qs}`,
  );
}

export async function adminGetMerchant(id: string) {
  return adminFetch<AdminMerchant>(`/api/v1/admin/merchants/${id}`);
}

export async function adminUpdateMerchant(
  id: string,
  payload: Record<string, unknown>,
) {
  return adminFetch<AdminMerchant>(`/api/v1/admin/merchants/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function adminDeleteMerchant(id: string) {
  return adminFetch<void>(`/api/v1/admin/merchants/${id}`, { method: "DELETE" });
}

export async function adminListMerchantDeals(merchantId: string) {
  return adminFetch<AdminDeal[]>(
    `/api/v1/admin/merchants/${merchantId}/deals?include_inactive=true`,
  );
}

export async function adminListDeals(q?: string, limit = 5000) {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (q?.trim()) qs.set("q", q.trim());
  return adminFetch<AdminDeal[]>(`/api/v1/admin/deals?${qs}`);
}

export async function adminGetDeal(dealId: string) {
  return adminFetch<AdminDeal>(`/api/v1/admin/deals/${dealId}`);
}

export async function adminCreateDeal(payload: Record<string, unknown>) {
  return adminFetch<AdminDeal>(`/api/v1/admin/deals`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function adminUpdateDeal(
  dealId: string,
  payload: Record<string, unknown>,
) {
  return adminFetch<AdminDeal>(`/api/v1/admin/deals/${dealId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function adminDeleteDeal(dealId: string) {
  return adminFetch<void>(`/api/v1/admin/deals/${dealId}`, { method: "DELETE" });
}
