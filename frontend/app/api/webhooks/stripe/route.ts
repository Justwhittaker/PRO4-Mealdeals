import { NextResponse } from "next/server";
import type Stripe from "stripe";
import { attachMonthlyPhaseAfterIntro } from "@/actions/stripe";
import {
  claimMerchantTrial,
  markDesignRequestPaid,
  updateMerchantSubscription,
} from "@/lib/api";
import {
  getStripe,
  phaseFromPlanMeta,
  phaseFromPriceId,
  tierFromPriceId,
  type SubscriptionPhase,
} from "@/lib/stripe";

export const runtime = "nodejs";

/**
 * Stripe webhook — Priority trial/promo + Design Special sync.
 */
export async function POST(req: Request) {
  const stripe = getStripe();
  const signature = req.headers.get("stripe-signature");
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  if (!signature || !webhookSecret) {
    return NextResponse.json(
      { error: "Missing Stripe webhook configuration" },
      { status: 400 },
    );
  }

  const body = await req.text();

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Invalid signature";
    return NextResponse.json({ error: message }, { status: 400 });
  }

  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        const merchantId = session.metadata?.merchantId;
        const plan = session.metadata?.plan;

        if (plan === "design_special") {
          const designRequestId = session.metadata?.designRequestId;
          if (!designRequestId) break;
          const pi =
            typeof session.payment_intent === "string"
              ? session.payment_intent
              : session.payment_intent?.id;
          const result = await markDesignRequestPaid(designRequestId, {
            stripe_checkout_session_id: session.id,
            stripe_payment_intent_id: pi,
          });
          if (!result.ok) {
            console.warn(
              "[stripe webhook] Failed to mark design request paid:",
              result.error,
              { designRequestId },
            );
          }
          break;
        }

        if (!merchantId) break;

        let tier = "featured";
        let phase: SubscriptionPhase = phaseFromPlanMeta(plan);
        const monthlyPriceId = session.metadata?.monthlyPriceId;

        if (session.subscription && typeof session.subscription === "string") {
          const sub = await stripe.subscriptions.retrieve(session.subscription);
          const priceId = sub.items.data[0]?.price.id;
          if (priceId && phase === "monthly") {
            tier = tierFromPriceId(priceId);
            phase = phaseFromPriceId(priceId);
          }
          // Free first month on the monthly price → Stripe status "trialing"
          if (sub.status === "trialing" || plan === "priority_trial") {
            phase = "trial";
            tier = "featured";
          }

          if (plan === "priority_promo" && monthlyPriceId) {
            try {
              await attachMonthlyPhaseAfterIntro(
                session.subscription,
                monthlyPriceId,
              );
            } catch (scheduleErr) {
              console.warn(
                "[stripe webhook] Could not attach monthly phase:",
                scheduleErr,
              );
            }
          }
        }

        if (plan === "priority_trial") {
          const claim = await claimMerchantTrial(merchantId);
          if (!claim.ok) {
            console.warn(
              "[stripe webhook] Trial claim failed:",
              claim.error,
              { merchantId },
            );
          }
        }

        const customerId =
          typeof session.customer === "string"
            ? session.customer
            : session.customer?.id;

        const result = await updateMerchantSubscription({
          merchantId,
          is_subscriber: true,
          tier_level: tier,
          deal_slot_limit: 3,
          subscription_phase: phase,
          ...(customerId ? { stripe_customer_id: customerId } : {}),
        });

        if (!result.ok) {
          console.warn(
            "[stripe webhook] Failed to update merchant subscription:",
            result.error,
            { merchantId, tier, phase },
          );
        }
        break;
      }
      case "customer.subscription.updated": {
        const sub = event.data.object as Stripe.Subscription;
        const merchantId = sub.metadata?.merchantId;
        if (!merchantId) break;
        const priceId = sub.items.data[0]?.price.id;
        const tier = priceId ? tierFromPriceId(priceId) : "featured";
        let phase: SubscriptionPhase = priceId
          ? phaseFromPriceId(priceId)
          : "monthly";
        if (sub.status === "trialing") phase = "trial";
        const active =
          sub.status === "active" || sub.status === "trialing";

        await updateMerchantSubscription({
          merchantId,
          is_subscriber: active,
          tier_level: active ? tier : "free",
          deal_slot_limit: active ? 3 : 0,
          subscription_phase: active ? phase : "none",
        });
        break;
      }
      case "customer.subscription.deleted": {
        const sub = event.data.object as Stripe.Subscription;
        const merchantId = sub.metadata?.merchantId;
        if (!merchantId) break;

        await updateMerchantSubscription({
          merchantId,
          is_subscriber: false,
          tier_level: "free",
          deal_slot_limit: 0,
          subscription_phase: "none",
        });
        break;
      }
      default: {
        const _exhaustive: string = event.type;
        void _exhaustive;
        break;
      }
    }
  } catch (err) {
    console.error("[stripe webhook] handler error", err);
    return NextResponse.json({ error: "Webhook handler failed" }, { status: 500 });
  }

  return NextResponse.json({ received: true });
}
