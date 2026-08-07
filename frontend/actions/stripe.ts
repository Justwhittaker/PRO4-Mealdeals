"use server";

import {
  designSpecialPriceId,
  ensureRecurringPrice,
  getStripe,
  TRIAL_DAYS,
} from "@/lib/stripe";
import { resolvePriorityAmounts } from "@/lib/subscription-pricing";
import type { CurrencyCode } from "@/lib/currency";
import { checkTrialEligibility } from "@/lib/api";

export type PriorityCheckoutKind = "trial" | "promo";

/**
 * Start Priority checkout.
 * - trial: free first month (card required) → monthly local price
 * - promo: pay 50% off next 3 months now → then monthly
 */
export async function createPriorityCheckoutSession(opts: {
  merchantId: string;
  countryCode: string;
  currency: CurrencyCode;
  kind: PriorityCheckoutKind;
}): Promise<{ url?: string; error?: string; contactPath?: string }> {
  try {
    const { merchantId, countryCode, currency, kind } = opts;

    if (kind === "trial") {
      const eligibility = await checkTrialEligibility(merchantId);
      if (!eligibility.ok) {
        return { error: eligibility.error };
      }
      if (!eligibility.data.eligible) {
        return {
          error:
            eligibility.data.reason ??
            "Free month is not available for this account.",
          contactPath: eligibility.data.contact_path ?? "/contact",
        };
      }
    }

    const amounts = await resolvePriorityAmounts(currency);
    const stripe = getStripe();
    const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

    const monthlyPriceId = await ensureRecurringPrice({
      lookupKey: `mealdeals_priority_monthly_${currency.toLowerCase()}`,
      currency,
      unitAmountCents: amounts.monthlyCents,
      intervalCount: 1,
      nickname: `Priority monthly ${currency}`,
    });

    if (kind === "trial") {
      const session = await stripe.checkout.sessions.create({
        mode: "subscription",
        line_items: [{ price: monthlyPriceId, quantity: 1 }],
        success_url: `${appUrl}/dashboard?success=1&plan=trial`,
        cancel_url: `${appUrl}/dashboard?canceled=1`,
        // Require card details up front (default) so billing can start after trial
        payment_method_collection: "always",
        customer_email: undefined,
        metadata: {
          merchantId,
          countryCode,
          currency,
          plan: "priority_trial",
          dealSlots: "3",
          monthlyPriceId,
        },
        subscription_data: {
          trial_period_days: TRIAL_DAYS,
          trial_settings: {
            end_behavior: { missing_payment_method: "cancel" },
          },
          metadata: {
            merchantId,
            countryCode,
            currency,
            plan: "priority_trial",
            dealSlots: "3",
            phase: "trial",
            monthlyPriceId,
          },
        },
        allow_promotion_codes: true,
      });

      if (!session.url) {
        return { error: "Stripe did not return a checkout URL" };
      }
      return { url: session.url };
    }

    // Pay now — 50% off three months, then monthly
    const promoPriceId = await ensureRecurringPrice({
      lookupKey: `mealdeals_priority_promo3_${currency.toLowerCase()}`,
      currency,
      unitAmountCents: amounts.promoCents,
      intervalCount: 3,
      nickname: `Priority promo 3mo ${currency}`,
    });

    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      line_items: [{ price: promoPriceId, quantity: 1 }],
      success_url: `${appUrl}/dashboard?success=1&plan=promo`,
      cancel_url: `${appUrl}/dashboard?canceled=1`,
      metadata: {
        merchantId,
        countryCode,
        currency,
        plan: "priority_promo",
        dealSlots: "3",
        monthlyPriceId,
      },
      subscription_data: {
        metadata: {
          merchantId,
          countryCode,
          currency,
          plan: "priority_promo",
          dealSlots: "3",
          phase: "promo",
          monthlyPriceId,
        },
      },
      allow_promotion_codes: true,
    });

    if (!session.url) {
      return { error: "Stripe did not return a checkout URL" };
    }
    return { url: session.url };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to create checkout session";
    return { error: message };
  }
}

/** @deprecated Use createPriorityCheckoutSession */
export async function createCheckoutSession(
  _priceId: string,
  merchantId: string,
  countryCode: string,
): Promise<{ url?: string; error?: string; contactPath?: string }> {
  return createPriorityCheckoutSession({
    merchantId,
    countryCode,
    currency: "EUR",
    kind: "trial",
  });
}

/**
 * One-time €20 Checkout for a Deal Design Special (slot-exempt, 2-month run).
 */
export async function createDesignCheckoutSession(
  designRequestId: string,
  merchantId: string,
): Promise<{ url?: string; error?: string }> {
  try {
    const stripe = getStripe();
    const priceId = designSpecialPriceId();
    const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${appUrl}/dashboard/design?paid=1&request=${designRequestId}`,
      cancel_url: `${appUrl}/dashboard/design?canceled=1&request=${designRequestId}`,
      metadata: {
        merchantId,
        designRequestId,
        plan: "design_special",
        slotExempt: "true",
        durationDays: "60",
      },
      payment_intent_data: {
        metadata: {
          merchantId,
          designRequestId,
          plan: "design_special",
        },
      },
      allow_promotion_codes: true,
    });

    if (!session.url) {
      return { error: "Stripe did not return a checkout URL" };
    }
    return { url: session.url };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to create design checkout";
    return { error: message };
  }
}

export async function createCustomerPortalSession(
  customerId: string,
): Promise<{ url?: string; error?: string }> {
  try {
    const stripe = getStripe();
    const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

    const session = await stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url: `${appUrl}/dashboard`,
    });

    return { url: session.url };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to open customer portal";
    return { error: message };
  }
}

/**
 * After promo (3-month) checkout, roll into monthly via Schedule.
 */
export async function attachMonthlyPhaseAfterIntro(
  subscriptionId: string,
  monthlyPriceIdValue: string,
): Promise<void> {
  const stripe = getStripe();
  const schedule = await stripe.subscriptionSchedules.create({
    from_subscription: subscriptionId,
  });

  const current = schedule.phases[0];
  if (!current?.items?.[0]?.price) return;

  const currentPrice =
    typeof current.items[0].price === "string"
      ? current.items[0].price
      : current.items[0].price.id;

  await stripe.subscriptionSchedules.update(schedule.id, {
    end_behavior: "release",
    phases: [
      {
        items: [{ price: currentPrice, quantity: 1 }],
        start_date: current.start_date,
        end_date: current.end_date ?? undefined,
      },
      {
        items: [{ price: monthlyPriceIdValue, quantity: 1 }],
      },
    ],
  });
}
