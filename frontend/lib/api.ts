import type { CurrencyCode } from "./currency";
import type { TierLevel } from "./priority";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Deal {
  id: string;
  title: string;
  description?: string;
  /** Scraped business about blurb (not the deal offer text). */
  aboutBlurb?: string | null;
  restaurantName: string;
  imageUrl?: string | null;
  logoUrl?: string | null;
  price: number;
  originalPrice?: number | null;
  currency: CurrencyCode;
  country: string;
  city: string;
  tier: TierLevel;
  isSubscriber?: boolean;
  isScraped?: boolean;
  distanceKm?: number | null;
  createdAt: string;
  affiliateUrl?: string | null;
  /** Destination without tracking params — preferred for display. */
  cleanUrl?: string | null;
  category?: string;
  savingsPercent?: number;
}

export interface ValueCalculatorResult {
  dealPrice: number;
  marketValue: number;
  savings: number;
  savingsPercent: number;
  currency: CurrencyCode;
  items?: { name: string; value: number }[];
}

export interface FeedParams {
  country?: string;
  city?: string;
  currency?: CurrencyCode;
  lat?: number;
  lng?: number;
  lon?: number;
  radiusKm?: number;
  /** Preferred over radiusKm — backend converts to km. */
  radiusMiles?: number;
  /** score = featured first; distance = nearest first */
  sort?: "score" | "distance";
  limit?: number;
}

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; status?: number };

/** Raw feed item from FastAPI (snake_case). */
interface BackendDealFeedItem {
  id: string;
  merchant_id: string;
  merchant_name: string;
  title?: string | null;
  description?: string | null;
  original_price: string | number;
  deal_price: string | number;
  currency_code: string;
  converted_deal_price?: string | number | null;
  converted_currency?: string | null;
  distance_km?: number | null;
  feed_score?: number;
  affiliate_url?: string | null;
  clean_url?: string | null;
  image_url?: string | null;
  logo_url?: string | null;
  created_at: string;
  expires_at?: string | null;
  city?: string | null;
  country_code?: string | null;
  tier_level?: string;
  is_subscriber?: boolean;
}

interface BackendValueCalculator {
  deal_id: string;
  deal_price: string | number;
  items_total: string | number;
  savings_amount: string | number;
  savings_percent: number;
  currency_code: string;
  items?: {
    item_name: string;
    individual_price: string | number;
  }[];
}

function toNumber(value: string | number | null | undefined): number {
  if (value == null) return 0;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

function slugifyCity(city: string): string {
  return city.trim().toLowerCase().replace(/\s+/g, "-");
}

function mapTier(tier: string | undefined, isSubscriber: boolean): TierLevel {
  if (!isSubscriber) return "scraped";
  if (tier === "enterprise" || tier === "featured" || tier === "free") {
    return tier;
  }
  return "free";
}

/** Drop placeholder / non-http media so the UI never paints a fake logo/photo. */
function cleanMediaUrl(value?: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^https?:\/\//i.test(trimmed)) return null;
  const lower = trimmed.toLowerCase();
  if (
    /(placeholder|sprite|pixel|1x1|tracking|spacer|blank\.gif)/i.test(lower)
  ) {
    return null;
  }
  return trimmed;
}

function mapFeedItem(
  item: BackendDealFeedItem,
  fallbackCountry?: string,
  fallbackCity?: string,
): Deal {
  const isSubscriber = Boolean(item.is_subscriber);
  const currency = (
    item.converted_currency ?? item.currency_code ?? "USD"
  ).toUpperCase() as CurrencyCode;
  const price = toNumber(item.converted_deal_price ?? item.deal_price);
  const original = toNumber(item.original_price);
  const savingsPercent =
    original > 0 ? Math.round(((original - price) / original) * 100) : undefined;

  const country = (
    item.country_code ??
    fallbackCountry ??
    "us"
  ).toLowerCase();
  const city = slugifyCity(item.city ?? fallbackCity ?? "city");

  return {
    id: item.id,
    title: item.title?.trim() || item.merchant_name,
    description: item.description ?? undefined,
    restaurantName: item.merchant_name,
    price,
    originalPrice: original || null,
    currency,
    country,
    city,
    tier: mapTier(item.tier_level, isSubscriber),
    isSubscriber,
    isScraped: !isSubscriber,
    distanceKm: item.distance_km ?? null,
    createdAt: item.created_at,
    affiliateUrl: item.affiliate_url ?? null,
    cleanUrl: item.clean_url ?? null,
    imageUrl: cleanMediaUrl(item.image_url),
    logoUrl: cleanMediaUrl(item.logo_url),
    savingsPercent:
      savingsPercent != null && savingsPercent > 0 ? savingsPercent : undefined,
  };
}

function mapValueCalculator(
  data: BackendValueCalculator,
): ValueCalculatorResult {
  return {
    dealPrice: toNumber(data.deal_price),
    marketValue: toNumber(data.items_total),
    savings: toNumber(data.savings_amount),
    savingsPercent: data.savings_percent,
    currency: data.currency_code.toUpperCase() as CurrencyCode,
    items: (data.items ?? []).map((item) => ({
      name: item.item_name,
      value: toNumber(item.individual_price),
    })),
  };
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit & { next?: { revalidate?: number | false } },
): Promise<ApiResult<T>> {
  const url = `${API_URL.replace(/\/$/, "")}${path}`;
  try {
    const { next, cache, ...rest } = init ?? {};
    const isServer = typeof window === "undefined";
    // Never mix cache: 'no-store' with next.revalidate — Next.js warns and can
    // leave the client bundle in a bad state during HMR.
    const cacheOpts =
      cache !== undefined
        ? { cache }
        : next !== undefined
          ? { next }
          : isServer
            ? { next: { revalidate: 30 as const } }
            : { cache: "no-store" as RequestCache };

    const res = await fetch(url, {
      ...rest,
      headers: {
        Accept: "application/json",
        ...(rest.headers ?? {}),
      },
      ...cacheOpts,
    });

    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = (await res.json()) as { detail?: string | { msg?: string }[] };
        if (typeof body.detail === "string") {
          detail = body.detail;
        } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
          detail = body.detail[0].msg;
        }
      } catch {
        // keep statusText
      }
      return {
        ok: false,
        error: detail || `API ${res.status}`,
        status: res.status,
      };
    }

    const data = (await res.json()) as T;
    return { ok: true, data };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Unable to reach the Dine A Deal API";
    return { ok: false, error: message };
  }
}

export async function fetchDealsFeed(
  params: FeedParams = {},
): Promise<ApiResult<Deal[]>> {
  const qs = new URLSearchParams();
  if (params.country) {
    const raw = params.country.toUpperCase();
    qs.set("country_code", raw === "UK" ? "GB" : raw);
  }
  if (params.city) {
    // Used for auto-scrape center city; radius mode uses lat/lon for inclusion
    qs.set("city", params.city.replace(/-/g, " "));
  }
  if (params.currency) qs.set("currency_override", params.currency);
  if (params.lat != null) qs.set("lat", String(params.lat));
  const lon = params.lon ?? params.lng;
  if (lon != null) qs.set("lon", String(lon));
  if (params.radiusMiles != null) {
    qs.set("radius_miles", String(params.radiusMiles));
  } else if (params.radiusKm != null) {
    qs.set("radius_km", String(params.radiusKm));
  }
  if (params.sort) qs.set("sort", params.sort);
  if (params.limit != null) qs.set("limit", String(params.limit));
  // Backend defaults to true; keep explicit so empty city pages auto-scrape.
  qs.set("auto_scrape", "true");

  const query = qs.toString();
  const result = await apiFetch<{ results?: BackendDealFeedItem[] } | BackendDealFeedItem[]>(
    `/api/v1/deals/feed${query ? `?${query}` : ""}`,
    { cache: "no-store" },
  );

  if (!result.ok) return result;

  const rows = Array.isArray(result.data)
    ? result.data
    : (result.data.results ?? []);

  return {
    ok: true,
    data: rows.map((row) =>
      mapFeedItem(row, params.country, params.city),
    ),
  };
}

export async function fetchDeal(
  id: string,
  opts?: { country?: string; city?: string },
): Promise<ApiResult<Deal>> {
  const result = await apiFetch<{
    id: string;
    affiliate_url?: string | null;
    clean_url?: string | null;
    image_url?: string | null;
    logo_url?: string | null;
    about_blurb?: string | null;
    original_price: string | number;
    deal_price: string | number;
    currency_code: string;
    created_at: string;
    translations?: { title: string; description: string; language_code?: string }[];
    merchant_id: string;
    merchant_name: string;
    tier_level?: string;
    is_subscriber?: boolean;
    city?: string | null;
    country_code?: string | null;
  }>(`/api/v1/deals/${id}`);

  if (!result.ok) return result;

  const d = result.data;
  const translation = d.translations?.[0];
  const isSubscriber = Boolean(d.is_subscriber);
  const country = (d.country_code ?? opts?.country ?? "us").toLowerCase();
  const city = slugifyCity(d.city ?? opts?.city ?? "city");

  return {
    ok: true,
    data: {
      id: d.id,
      title: translation?.title?.trim() || d.merchant_name,
      description: translation?.description,
      aboutBlurb: d.about_blurb ?? null,
      restaurantName: d.merchant_name,
      price: toNumber(d.deal_price),
      originalPrice: toNumber(d.original_price) || null,
      currency: d.currency_code.toUpperCase() as CurrencyCode,
      country,
      city,
      tier: mapTier(d.tier_level, isSubscriber),
      isSubscriber,
      isScraped: !isSubscriber,
      createdAt: d.created_at,
      affiliateUrl: d.affiliate_url ?? null,
      cleanUrl: d.clean_url ?? null,
      imageUrl: cleanMediaUrl(d.image_url),
      logoUrl: cleanMediaUrl(d.logo_url),
    },
  };
}

export async function fetchValueCalculator(
  id: string,
): Promise<ApiResult<ValueCalculatorResult>> {
  const result = await apiFetch<BackendValueCalculator>(
    `/api/v1/deals/${id}/value-calculator`,
    { cache: "no-store" },
  );
  if (!result.ok) return result;
  return { ok: true, data: mapValueCalculator(result.data) };
}

/** Preview calculator for new deals (no persisted id yet). */
export async function previewValueCalculator(input: {
  dealPrice: number;
  items: { name: string; value: number }[];
  currency: CurrencyCode;
}): Promise<ApiResult<ValueCalculatorResult>> {
  const marketValue = input.items.reduce((sum, i) => sum + i.value, 0);
  const savings = Math.max(0, marketValue - input.dealPrice);
  const savingsPercent =
    marketValue > 0 ? Math.round((savings / marketValue) * 100) : 0;

  return {
    ok: true,
    data: {
      dealPrice: input.dealPrice,
      marketValue,
      savings,
      savingsPercent,
      currency: input.currency,
      items: input.items,
    },
  };
}

export async function updateMerchantSubscription(payload: {
  merchantId: string;
  is_subscriber: boolean;
  tier_level: string;
  deal_slot_limit?: number;
  subscription_phase?: string;
  stripe_customer_id?: string;
}): Promise<ApiResult<{ ok: boolean }>> {
  const result = await apiFetch<{ id: string }>(
    `/api/v1/merchants/${payload.merchantId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        is_subscriber: payload.is_subscriber,
        tier_level: payload.tier_level,
        deal_slot_limit: payload.deal_slot_limit,
        subscription_phase: payload.subscription_phase,
        ...(payload.stripe_customer_id
          ? { stripe_customer_id: payload.stripe_customer_id }
          : {}),
      }),
      cache: "no-store",
    },
  );

  if (!result.ok) return result;
  return { ok: true, data: { ok: true } };
}

/** Trigger area scrape (city pages also auto-scrape via empty feed). */
export async function scrapeAreaDeals(
  country: string,
  city: string,
): Promise<ApiResult<{ ingested?: number; status: string }>> {
  const qs = new URLSearchParams({
    country_code: country.toUpperCase() === "UK" ? "GB" : country.toUpperCase(),
    city: city.replace(/-/g, " "),
    wait: "true",
  });
  return apiFetch(`/api/v1/scrapers/area?${qs}`, {
    method: "POST",
    cache: "no-store",
  });
}

export function getGoRedirectUrl(dealId: string): string {
  return `${API_URL.replace(/\/$/, "")}/go/${dealId}`;
}

export interface MerchantProfile {
  id: string;
  name: string;
  email?: string | null;
  contact_name?: string | null;
  phone?: string | null;
  website?: string | null;
  bio?: string | null;
  logo_url?: string | null;
  is_subscriber: boolean;
  tier_level: string;
  deal_slot_limit: number;
  subscription_phase: string;
  stripe_customer_id?: string | null;
  active_deal_count: number;
  total_deal_count: number;
  open_slots: number;
  used_free_trial?: boolean;
  location?: {
    country_code: string;
    city: string;
  } | null;
}

export interface TrialEligibility {
  eligible: boolean;
  reason?: string | null;
  contact_path: string;
}

export async function checkTrialEligibility(
  merchantId: string,
): Promise<ApiResult<TrialEligibility>> {
  return apiFetch(`/api/v1/merchants/${merchantId}/trial-eligibility`, {
    cache: "no-store",
  });
}

export async function claimMerchantTrial(
  merchantId: string,
): Promise<ApiResult<{ claimed: boolean; message: string }>> {
  return apiFetch(`/api/v1/merchants/${merchantId}/claim-trial`, {
    method: "POST",
    cache: "no-store",
  });
}

export interface HistoryDeal {
  id: string;
  merchant_id: string;
  deal_price: number;
  original_price: number;
  currency_code: string;
  is_active: boolean;
  created_at: string;
  slot_exempt?: boolean;
  reposted_from_id?: string | null;
  title?: string;
  translations?: { title: string; description: string }[];
}

export async function fetchMerchantProfile(
  merchantId: string,
): Promise<ApiResult<MerchantProfile>> {
  return apiFetch(`/api/v1/merchants/${merchantId}/profile`, {
    cache: "no-store",
  });
}

export async function updateMerchantProfile(
  merchantId: string,
  payload: Partial<{
    name: string;
    email: string;
    contact_name: string;
    phone: string;
    website: string;
    bio: string;
  }>,
): Promise<ApiResult<MerchantProfile>> {
  return apiFetch(`/api/v1/merchants/${merchantId}/profile`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

export async function fetchDealHistory(
  merchantId: string,
): Promise<
  ApiResult<{
    count: number;
    active_count: number;
    open_slots: number;
    results: HistoryDeal[];
  }>
> {
  const result = await apiFetch<{
    count: number;
    active_count: number;
    open_slots: number;
    results: HistoryDeal[];
  }>(`/api/v1/merchants/${merchantId}/deals/history?include_inactive=true`, {
    cache: "no-store",
  });
  if (!result.ok) return result;
  return {
    ok: true,
    data: {
      ...result.data,
      results: result.data.results.map((d) => ({
        ...d,
        deal_price: toNumber(d.deal_price),
        original_price: toNumber(d.original_price),
        title: d.translations?.[0]?.title,
      })),
    },
  };
}

export async function repostDeal(
  merchantId: string,
  dealId: string,
): Promise<ApiResult<{ message: string; deal: { id: string } }>> {
  return apiFetch(`/api/v1/merchants/${merchantId}/deals/${dealId}/repost`, {
    method: "POST",
    cache: "no-store",
  });
}

export async function setDealActive(
  dealId: string,
  isActive: boolean,
): Promise<ApiResult<{ id: string; is_active: boolean }>> {
  return apiFetch(`/api/v1/deals/${dealId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: isActive }),
    cache: "no-store",
  });
}

export async function createMerchantDeal(payload: {
  merchant_id: string;
  title: string;
  description?: string;
  deal_price: number;
  original_price: number;
  currency_code: string;
  items: { item_name: string; individual_price: number; category?: string }[];
}): Promise<ApiResult<{ id: string }>> {
  return apiFetch("/api/v1/deals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      merchant_id: payload.merchant_id,
      title: payload.title,
      description: payload.description ?? payload.title,
      deal_price: payload.deal_price,
      original_price: payload.original_price,
      currency_code: payload.currency_code,
      is_active: true,
      slot_exempt: false,
      items: payload.items.map((item) => ({
        item_name: item.item_name,
        individual_price: item.individual_price,
        category: item.category ?? "main",
      })),
    }),
    cache: "no-store",
  });
}

export interface DesignRequest {
  id: string;
  merchant_id: string;
  title: string;
  description: string;
  details: string;
  photo_urls: string[];
  status: string;
  deal_id?: string | null;
  fulfillment_image_url?: string | null;
  created_at: string;
  paid_at?: string | null;
  posted_at?: string | null;
}

export async function createDesignRequest(payload: {
  merchant_id: string;
  title: string;
  description: string;
  details: string;
  photo_urls: string[];
}): Promise<ApiResult<DesignRequest>> {
  return apiFetch("/api/v1/design-requests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

export async function listDesignRequests(
  merchantId: string,
): Promise<ApiResult<{ count: number; results: DesignRequest[] }>> {
  return apiFetch(
    `/api/v1/design-requests?merchant_id=${merchantId}&limit=50`,
    { cache: "no-store" },
  );
}

export async function markDesignRequestPaid(
  requestId: string,
  payload: {
    stripe_checkout_session_id?: string;
    stripe_payment_intent_id?: string;
  },
): Promise<ApiResult<DesignRequest>> {
  return apiFetch(`/api/v1/design-requests/${requestId}/mark-paid`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

export async function fulfillDesignRequest(
  requestId: string,
  payload: {
    image_url: string;
    title?: string;
    description?: string;
    deal_price?: number;
    original_price?: number;
    currency_code?: string;
  },
): Promise<ApiResult<{ message: string; deal: { id: string } }>> {
  const secret =
    process.env.DESIGN_FULFILL_SECRET ?? "mealdeals-design";
  return apiFetch(`/api/v1/design-requests/${requestId}/fulfill`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Design-Fulfill-Secret": secret,
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

export interface NewsletterSubscriber {
  id: string;
  name: string;
  surname: string;
  email: string;
  location: string;
  country_code?: string | null;
  city?: string | null;
  is_subscribed: boolean;
  unsubscribed_at?: string | null;
  created_at: string;
}

export interface NewsletterAction {
  message: string;
  email: string;
  is_subscribed: boolean;
}

export interface NewsletterStatus {
  email: string;
  is_subscribed: boolean;
  exists: boolean;
}

export async function subscribeNewsletter(payload: {
  name: string;
  surname: string;
  email: string;
  location: string;
  country_code?: string;
  city?: string;
}): Promise<ApiResult<NewsletterSubscriber>> {
  return apiFetch("/api/v1/newsletter/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

export async function unsubscribeNewsletter(
  token: string,
): Promise<ApiResult<NewsletterAction>> {
  const qs = new URLSearchParams({ token });
  return apiFetch(`/api/v1/newsletter/unsubscribe?${qs}`, {
    method: "POST",
    cache: "no-store",
  });
}

export async function resubscribeNewsletter(payload: {
  email: string;
  token?: string;
}): Promise<ApiResult<NewsletterAction>> {
  return apiFetch("/api/v1/newsletter/resubscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

export async function getNewsletterStatus(
  email: string,
): Promise<ApiResult<NewsletterStatus>> {
  const qs = new URLSearchParams({ email });
  return apiFetch(`/api/v1/newsletter/status?${qs}`, {
    cache: "no-store",
  });
}

export { API_URL };
