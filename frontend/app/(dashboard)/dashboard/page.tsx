import Link from "next/link";
import { cookies, headers } from "next/headers";
import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BillingActions } from "@/components/merchant/BillingActions";
import { authOptions } from "@/lib/auth";
import { checkTrialEligibility, fetchMerchantProfile } from "@/lib/api";
import { currencyForCountry, formatMoney } from "@/lib/currency";
import {
  LOCATION_COOKIE,
  parseLocationCookie,
  resolveGeoFromHeaders,
} from "@/lib/geo";
import { DEAL_SLOT_LIMIT, DESIGN_SPECIAL } from "@/lib/stripe";
import { resolvePriorityAmounts } from "@/lib/subscription-pricing";

function resolveBillingCountry(merchantCountry?: string | null): string {
  if (merchantCountry) {
    return merchantCountry.toLowerCase() === "gb"
      ? "uk"
      : merchantCountry.toLowerCase();
  }
  const pref = parseLocationCookie(cookies().get(LOCATION_COOKIE)?.value);
  if (pref) return pref.countryCode;
  const geo = resolveGeoFromHeaders(headers());
  if (geo) return geo.countryCode;
  return "uk";
}

export default async function DealOfTheCenturyPage({
  searchParams,
}: {
  searchParams?: { success?: string; canceled?: string; plan?: string };
}) {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/dashboard");

  const merchantId = session.user.id;
  const profile = await fetchMerchantProfile(merchantId);
  const countryCode = resolveBillingCountry(
    profile.ok ? profile.data.location?.country_code : null,
  );
  const currency = currencyForCountry(countryCode);
  const amounts = await resolvePriorityAmounts(currency);

  const eligibility = profile.ok
    ? await checkTrialEligibility(merchantId)
    : { ok: false as const, error: "Profile unavailable" };

  const trialEligible = eligibility.ok ? eligibility.data.eligible : false;
  const trialReason = eligibility.ok
    ? eligibility.data.reason
    : "Complete your merchant profile before starting Priority.";
  const contactPath =
    eligibility.ok && eligibility.data.contact_path
      ? eligibility.data.contact_path
      : "/contact";

  const isSubscriber = profile.ok ? profile.data.is_subscriber : false;
  const openSlots = profile.ok ? profile.data.open_slots : 0;
  const phase = profile.ok ? profile.data.subscription_phase : undefined;

  return (
    <div className="space-y-10">
      <div>
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
          Merchant portal
        </p>
        <h1 className="mt-1 font-display text-3xl text-charcoal-50 sm:text-4xl">
          Deal of the century
        </h1>
        <p className="mt-2 max-w-2xl text-charcoal-400">
          Your Priority subscription landing page — pick a plan, unlock{" "}
          {DEAL_SLOT_LIMIT} slots, then publish deals that rank above scraped
          listings. Or skip the quota with Design Deals 4 U.
        </p>
      </div>

      {searchParams?.success ? (
        <div className="rounded-lg border border-burgundy-200 bg-burgundy-50 px-4 py-3 text-sm text-charcoal-200">
          Checkout completed
          {searchParams.plan === "trial"
            ? " — your free month is active once Stripe confirms the card."
            : searchParams.plan === "promo"
              ? " — your discounted three months will activate via webhook."
              : ". Your subscription activates once the Stripe webhook confirms."}
        </div>
      ) : null}
      {searchParams?.canceled ? (
        <div className="rounded-lg border border-charcoal-600 bg-charcoal-900/60 px-4 py-3 text-sm text-charcoal-300">
          Checkout canceled — no charge was made.
        </div>
      ) : null}

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl text-charcoal-50">
              Priority subscription
            </h2>
            <p className="mt-1 text-sm text-charcoal-400">
              First month free (card on file), then{" "}
              {formatMoney(amounts.monthly, currency)}/month — or pay{" "}
              {formatMoney(amounts.promoThreeMonths, currency)} now for 50% off
              three months.
            </p>
          </div>
          {isSubscriber ? (
            <Badge variant="verified">
              Active{phase ? ` · ${phase}` : ""} · {openSlots} open slots
            </Badge>
          ) : (
            <Badge variant="outline">No subscription yet</Badge>
          )}
        </div>

        <BillingActions
          merchantId={merchantId}
          countryCode={countryCode}
          currency={currency}
          monthlyAmount={amounts.monthly}
          promoAmount={amounts.promoThreeMonths}
          trialEligible={trialEligible}
          trialReason={trialReason}
          contactPath={contactPath}
          stripeCustomerId={
            profile.ok ? profile.data.stripe_customer_id ?? null : null
          }
          isSubscriber={isSubscriber}
          subscriptionPhase={phase}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Publish Priority deals</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-charcoal-400">
            {isSubscriber ? (
              <p>
                You have {openSlots} open slot
                {openSlots === 1 ? "" : "s"}. Create a deal or manage history.
              </p>
            ) : (
              <p>
                Choose a subscription above before you can add a new Priority
                deal.
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              {isSubscriber ? (
                <Button asChild>
                  <Link href="/dashboard/deals/new">Create a Priority deal</Link>
                </Button>
              ) : (
                <Button disabled type="button">
                  Subscribe first
                </Button>
              )}
              <Button asChild variant="outline">
                <Link href="/dashboard/deals">Deal history</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-burgundy-300/40">
          <CardHeader>
            <div className="flex flex-wrap gap-2">
              <Badge variant="featured">Design Deals 4 U</Badge>
              <Badge variant="outline">Slot-exempt</Badge>
            </div>
            <CardTitle className="mt-2 text-xl">
              {formatMoney(DESIGN_SPECIAL.amount, DESIGN_SPECIAL.currency)} per
              deal
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-charcoal-400">
            <p>
              We design from your brief + photos. Does not use Priority slots —
              specials can run for two months.
            </p>
            <Button asChild variant="outline">
              <Link href="/dashboard/design">Open Design Deals 4 U</Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      <div className="flex flex-wrap gap-3">
        <Button asChild size="lg" variant="outline">
          <Link href="/dashboard/profile">Your profile</Link>
        </Button>
      </div>
    </div>
  );
}
