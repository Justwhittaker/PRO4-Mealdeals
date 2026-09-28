"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  createPriorityCheckoutSession,
  type PriorityCheckoutKind,
} from "@/actions/stripe";
import { formatMoney, type CurrencyCode } from "@/lib/currency";
import { DEAL_SLOT_LIMIT } from "@/lib/stripe";

interface BillingActionsProps {
  merchantId: string;
  countryCode: string;
  currency: CurrencyCode;
  monthlyAmount: number;
  promoAmount: number;
  trialEligible: boolean;
  trialReason?: string | null;
  contactPath: string;
  isSubscriber?: boolean;
  subscriptionPhase?: string;
}

export function BillingActions({
  merchantId,
  countryCode,
  currency,
  monthlyAmount,
  promoAmount,
  trialEligible,
  trialReason,
  contactPath,
  isSubscriber,
  subscriptionPhase,
}: BillingActionsProps) {
  const [error, setError] = useState<string | null>(null);
  const [contactHint, setContactHint] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);

  const promoFullPrice = monthlyAmount * 3;

  async function checkout(kind: PriorityCheckoutKind) {
    setLoading(kind);
    setError(null);
    setContactHint(false);
    try {
      const result = await createPriorityCheckoutSession({
        merchantId,
        countryCode,
        currency,
        kind,
      });
      if (result.url) {
        window.location.assign(result.url);
        return;
      }
      setError(result.error ?? "Checkout failed");
      setContactHint(Boolean(result.contactPath));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Checkout failed — check Stripe is configured on the server.",
      );
    }
    setLoading(null);
  }

  return (
    <div className="space-y-6">
      <Card className="border-burgundy-500/50 shadow-sm">
        <CardHeader>
          <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
            Recommended
          </p>
          <CardTitle className="text-xl">Priority Slots</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <p className="text-charcoal-300">
            Prices shown in{" "}
            <span className="font-medium text-charcoal-50">{currency}</span>{" "}
            for your area. You get{" "}
            <span className="text-burgundy-600">
              {DEAL_SLOT_LIMIT} active deal slots
            </span>{" "}
            that rank above scraped listings.
          </p>

          {isSubscriber ? (
            <p className="rounded-md border border-charcoal-700 bg-charcoal-900/40 px-3 py-2 text-sm text-charcoal-200">
              Active subscription
              {subscriptionPhase ? ` · phase: ${subscriptionPhase}` : ""}. Manage
              billing in the customer portal on{" "}
              <Link
                href="/dashboard/profile"
                className="font-medium text-burgundy-600 underline-offset-2 hover:underline"
              >
                your profile
              </Link>
              .
            </p>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-burgundy-500/40 bg-white p-4">
              <p className="text-xs uppercase tracking-wider text-charcoal-500">
                First month
              </p>
              <p className="mt-1 font-display text-3xl text-burgundy-500">
                Free
              </p>
              <p className="mt-1 text-sm text-charcoal-400">
                Free month on the monthly plan · {DEAL_SLOT_LIMIT} slots · card
                required
              </p>
            </div>
            <div className="rounded-xl border border-charcoal-700 bg-white p-4">
              <p className="text-xs uppercase tracking-wider text-charcoal-500">
                Then monthly
              </p>
              <p className="mt-1 font-display text-3xl text-charcoal-100">
                {formatMoney(monthlyAmount, currency)}
              </p>
              <p className="mt-1 text-sm text-charcoal-400">
                /month · same {DEAL_SLOT_LIMIT} slots
              </p>
            </div>
          </div>

          <Button
            className="h-auto min-h-12 w-full whitespace-normal px-4 py-3 text-center text-sm leading-snug tracking-wide sm:px-6 sm:text-base"
            size="lg"
            disabled={loading !== null || !trialEligible || Boolean(isSubscriber)}
            onClick={() => void checkout("trial")}
          >
            {loading === "trial" ? "Redirecting…" : "Start free month"}
          </Button>
          {!trialEligible ? (
            <p className="text-sm text-amber-800">
              {trialReason ??
                "Free month already used for this email, business, or location."}{" "}
              <Link
                href={contactPath}
                className="font-medium text-burgundy-600 underline-offset-2 hover:underline"
              >
                Contact us
              </Link>
            </p>
          ) : (
            <p className="text-xs text-charcoal-500">
              Primary option: monthly Priority with the first month free. Add a
              card at checkout — we charge{" "}
              {formatMoney(monthlyAmount, currency)}/month after 30 days unless
              you cancel in the portal.
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="border-charcoal-700/80 bg-charcoal-950/20">
        <CardHeader className="pb-2">
          <p className="text-[10px] font-medium uppercase tracking-wider text-charcoal-500">
            Or pay upfront
          </p>
          <CardTitle className="text-lg text-charcoal-100">
            Pay now — 50% off 3 months
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-charcoal-300">
            {formatMoney(promoAmount, currency)} = 3 months at 50% off (half of{" "}
            {formatMoney(monthlyAmount, currency)}×3 — normally{" "}
            {formatMoney(promoFullPrice, currency)}), then{" "}
            {formatMoney(monthlyAmount, currency)}/mo.
          </p>
          <Button
            className="h-auto min-h-11 w-full whitespace-normal px-4 py-2.5 text-center text-sm leading-snug tracking-wide"
            size="lg"
            variant="outline"
            disabled={loading !== null || Boolean(isSubscriber)}
            onClick={() => void checkout("promo")}
          >
            {loading === "promo"
              ? "Redirecting…"
              : `Pay ${formatMoney(promoAmount, currency)} now`}
          </Button>
        </CardContent>
      </Card>

      {error ? (
        <p className="text-sm text-amber-800" role="alert">
          {error}
          {contactHint ? (
            <>
              {" "}
              <Link
                href={contactPath}
                className="font-medium text-burgundy-600 underline-offset-2 hover:underline"
              >
                Contact us
              </Link>
            </>
          ) : null}
        </p>
      ) : null}
    </div>
  );
}
