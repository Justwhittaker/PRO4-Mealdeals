import Stripe from "stripe";
import type { CurrencyCode } from "./currency";

let stripeClient: Stripe | null = null;

export function getStripe(): Stripe {
  if (!stripeClient) {
    const key = process.env.STRIPE_SECRET_KEY;
    if (!key) {
      throw new Error("STRIPE_SECRET_KEY is not configured");
    }
    stripeClient = new Stripe(key, {
      apiVersion: "2025-02-24.acacia",
      typescript: true,
    });
  }
  return stripeClient;
}

/**
 * Priority Slots:
 * - Free first month (card required) → 3 slots
 * - Then €20/month (or geo-converted currency)
 * - Pay-now CTA: 50% off next 3 months = €30 (or converted) then monthly
 */
export type PlanTier = "free" | "priority" | "featured" | "enterprise";

export type SubscriptionPhase =
  | "none"
  | "trial"
  | "promo"
  | "monthly"
  | "intro";

export interface PlanPrice {
  tier: PlanTier;
  currency: CurrencyCode;
  amount: number;
  interval: "month" | "year";
  intervalCount?: number;
  envKey?: string;
  label: string;
  description: string;
  dealSlots: number;
  phase: SubscriptionPhase;
}

export const DEAL_SLOT_LIMIT = 3;
export const TRIAL_DAYS = 30;

/** EUR base amounts — other currencies convert via FX. */
export const PRIORITY_EUR = {
  monthly: 20,
  /** 50% off 3×€20 = €30 for three months */
  promoThreeMonths: 30,
} as const;

/** One-time €20 designed special — does not use Priority slots; lives 60 days. */
export const DESIGN_SPECIAL = {
  amount: 20,
  currency: "EUR" as CurrencyCode,
  durationDays: 60,
  envKey: "STRIPE_PRICE_DESIGN_SPECIAL_EUR",
  label: "Design Deals 4 U",
  description:
    "Design Deals 4 U — we design your deal from your brief + photos. €20 per deal. Does not use your 3 Priority posts — and the special can run for two months.",
};

export function designSpecialPriceId(): string {
  return (
    process.env.STRIPE_PRICE_DESIGN_SPECIAL_EUR ??
    "price_1U1XrbIFzPFZzgCPuc4R4rfO"
  );
}

/** Fallback display plans (EUR). UI prefers geo-converted amounts. */
export const PLANS: PlanPrice[] = [
  {
    tier: "priority",
    currency: "EUR",
    amount: 0,
    interval: "month",
    intervalCount: 1,
    label: "Priority — Monthly (first month free)",
    description:
      "Monthly Priority with the first month free and 3 slots. Card required — local monthly rate starts after 30 days.",
    dealSlots: DEAL_SLOT_LIMIT,
    phase: "trial",
  },
  {
    tier: "priority",
    currency: "EUR",
    amount: PRIORITY_EUR.promoThreeMonths,
    interval: "month",
    intervalCount: 3,
    label: "Priority — Pay now (50% off)",
    description:
      "Skip the wait — pay 50% off the next three months (€30 / local equiv.), then continue monthly.",
    dealSlots: DEAL_SLOT_LIMIT,
    phase: "promo",
  },
  {
    tier: "priority",
    currency: "EUR",
    amount: PRIORITY_EUR.monthly,
    interval: "month",
    intervalCount: 1,
    envKey: "STRIPE_PRICE_PRIORITY_MONTHLY_EUR",
    label: "Priority — Monthly",
    description: "€20/month (or converted) keeps your 3 priority slots.",
    dealSlots: DEAL_SLOT_LIMIT,
    phase: "monthly",
  },
];

export const PRIORITY_CHECKOUT_PLAN = PLANS[0];

function productId(): string | undefined {
  return process.env.STRIPE_PRODUCT_PRIORITY_ID;
}

/**
 * Get or create a recurring Stripe price by lookup_key (geo currency safe).
 */
export async function ensureRecurringPrice(opts: {
  lookupKey: string;
  currency: CurrencyCode;
  unitAmountCents: number;
  intervalCount: number;
  nickname: string;
}): Promise<string> {
  const stripe = getStripe();
  const existing = await stripe.prices.list({
    lookup_keys: [opts.lookupKey],
    active: true,
    limit: 1,
  });
  if (existing.data[0]?.id) {
    return existing.data[0].id;
  }

  let product = productId();
  if (!product) {
    const products = await stripe.products.list({
      limit: 20,
      active: true,
    });
    const found = products.data.find(
      (p) =>
        p.name.toLowerCase().includes("priority") ||
        p.metadata?.plan === "priority",
    );
    if (found) {
      product = found.id;
    } else {
      const created = await stripe.products.create({
        name: "DineADeal Priority Slots",
        metadata: { plan: "priority", dealSlots: "3" },
      });
      product = created.id;
    }
  }

  const price = await stripe.prices.create({
    product,
    currency: opts.currency.toLowerCase(),
    unit_amount: opts.unitAmountCents,
    recurring: {
      interval: "month",
      interval_count: opts.intervalCount,
    },
    lookup_key: opts.lookupKey,
    transfer_lookup_key: true,
    nickname: opts.nickname,
    metadata: {
      plan: "priority",
      dealSlots: "3",
      lookupKey: opts.lookupKey,
    },
  });
  return price.id;
}

export function monthlyPriceId(currency?: CurrencyCode): string | undefined {
  if (!currency || currency === "EUR") {
    return process.env.STRIPE_PRICE_PRIORITY_MONTHLY_EUR;
  }
  return process.env[`STRIPE_PRICE_PRIORITY_MONTHLY_${currency}`];
}

export function promoPriceId(currency?: CurrencyCode): string | undefined {
  if (!currency || currency === "EUR") {
    return process.env.STRIPE_PRICE_PRIORITY_PROMO_EUR;
  }
  return process.env[`STRIPE_PRICE_PRIORITY_PROMO_${currency}`];
}

export function tierFromPriceId(priceId: string): "featured" {
  void priceId;
  return "featured";
}

export function phaseFromPriceId(priceId: string): SubscriptionPhase {
  const monthly = process.env.STRIPE_PRICE_PRIORITY_MONTHLY_EUR;
  if (monthly && priceId === monthly) return "monthly";
  const promo = process.env.STRIPE_PRICE_PRIORITY_PROMO_EUR;
  if (promo && priceId === promo) return "promo";
  const entries = Object.entries(process.env).filter(([k]) =>
    k.startsWith("STRIPE_PRICE_"),
  );
  for (const [key, value] of entries) {
    if (value !== priceId) continue;
    if (key.includes("MONTHLY")) return "monthly";
    if (key.includes("PROMO")) return "promo";
    if (key.includes("INTRO")) return "promo";
  }
  return "monthly";
}

export function phaseFromPlanMeta(
  plan: string | undefined,
): SubscriptionPhase {
  switch (plan) {
    case "priority_trial":
      return "trial";
    case "priority_promo":
      return "promo";
    case "priority":
      return "monthly";
    default:
      return "monthly";
  }
}
