"use server";

import {
  DEAL_SLOT_LIMIT,
  designSpecialPriceId,
  ensureRecurringPrice,
  getStripe,
  phaseFromPlanMeta,
  TRIAL_DAYS,
  type SubscriptionPhase,
} from "@/lib/stripe";
import { resolvePriorityAmounts } from "@/lib/subscription-pricing";
import type { CurrencyCode } from "@/lib/currency";
import {
  checkTrialEligibility,
  claimMerchantTrial,
  updateMerchantSubscription,
} from "@/lib/api";

export type PriorityCheckoutKind = "trial" | "promo";

/**
 * Start Priority checkout.
 * - trial: monthly subscription with first month free (card required), then local monthly price
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
      // Free first month = Stripe trial on the monthly recurring price (not a separate product).
      const session = await stripe.checkout.sessions.create({
        mode: "subscription",
        line_items: [{ price: monthlyPriceId, quantity: 1 }],
        success_url: `${appUrl}/dashboard/profile?success=1&plan=trial`,
        cancel_url: `${appUrl}/dashboard?canceled=1`,
        // Card required now so month 2+ can bill automatically after the free month.
        payment_method_collection: "always",
        customer_email: undefined,
        metadata: {
          merchantId,
          countryCode,
          currency,
          plan: "priority_trial",
          billing: "monthly_with_free_first_month",
          dealSlots: String(DEAL_SLOT_LIMIT),
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
            billing: "monthly_with_free_first_month",
            dealSlots: String(DEAL_SLOT_LIMIT),
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
      success_url: `${appUrl}/dashboard/profile?success=1&plan=promo`,
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
      return_url: `${appUrl}/dashboard/profile`,
    });

    return { url: session.url };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to open customer portal";
    return { error: message };
  }
}

/**
 * After Checkout return (or if webhooks lag), activate Priority from Stripe.
 * Free month = trialing monthly subscription → treat as subscriber with slots.
 */
export async function syncMerchantPriorityFromStripe(
  merchantId: string,
): Promise<{ synced: boolean; phase?: SubscriptionPhase; error?: string }> {
  try {
    const stripe = getStripe();
    const sessions = await stripe.checkout.sessions.list({
      limit: 40,
      status: "complete",
    });
    const session = sessions.data.find(
      (item) =>
        item.metadata?.merchantId === merchantId &&
        item.mode === "subscription" &&
        (item.payment_status === "paid" ||
          item.payment_status === "no_payment_required"),
    );
    if (!session) {
      return { synced: false, error: "No completed Priority checkout found" };
    }

    const plan = session.metadata?.plan;
    let phase: SubscriptionPhase = phaseFromPlanMeta(plan);
    if (session.subscription && typeof session.subscription === "string") {
      const sub = await stripe.subscriptions.retrieve(session.subscription);
      if (sub.status === "trialing") {
        // Free first month of the monthly subscription
        phase = "trial";
      } else if (sub.status === "active") {
        phase = plan === "priority_promo" ? "promo" : "monthly";
      } else if (
        sub.status === "canceled" ||
        sub.status === "unpaid" ||
        sub.status === "incomplete_expired"
      ) {
        return { synced: false, error: `Subscription status is ${sub.status}` };
      }
    }

    if (plan === "priority_trial") {
      await claimMerchantTrial(merchantId);
    }

    const customerId =
      typeof session.customer === "string"
        ? session.customer
        : session.customer?.id;

    const result = await updateMerchantSubscription({
      merchantId,
      is_subscriber: true,
      tier_level: "featured",
      deal_slot_limit: DEAL_SLOT_LIMIT,
      subscription_phase: phase,
      ...(customerId ? { stripe_customer_id: customerId } : {}),
    });

    if (!result.ok) {
      return { synced: false, error: result.error };
    }
    return { synced: true, phase };
  } catch (err) {
    return {
      synced: false,
      error:
        err instanceof Error
          ? err.message
          : "Failed to sync Priority subscription from Stripe",
    };
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
