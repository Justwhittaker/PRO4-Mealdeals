import Link from "next/link";
import { cookies, headers } from "next/headers";
import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { syncMerchantPriorityFromStripe } from "@/actions/stripe";
import { Button } from "@/components/ui/button";
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
import { DEAL_SLOT_LIMIT } from "@/lib/stripe";
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
  let profile = await fetchMerchantProfile(merchantId);

  // Legacy Stripe success URLs still hit /dashboard — sync then send to profile.
  if (searchParams?.success === "1") {
    const sync = await syncMerchantPriorityFromStripe(merchantId);
    if (sync.synced) {
      profile = await fetchMerchantProfile(merchantId);
    }
    const params = new URLSearchParams({ success: "1" });
    if (searchParams.plan) params.set("plan", searchParams.plan);
    redirect(`/dashboard/profile?${params.toString()}`);
  }

  // Hide Deal of the century once Priority is active.
  if (profile.ok && profile.data.is_subscriber) {
    redirect("/dashboard/profile");
  }

  // Webhook lag: try activating Priority before showing the upsell.
  if (profile.ok && !profile.data.is_subscriber) {
    const sync = await syncMerchantPriorityFromStripe(merchantId);
    if (sync.synced) {
      profile = await fetchMerchantProfile(merchantId);
      if (profile.ok && profile.data.is_subscriber) {
        redirect("/dashboard/profile");
      }
    }
  }

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
  const phase = profile.ok ? profile.data.subscription_phase : undefined;

  return (
    <div className="space-y-10 text-center sm:text-left">
      <div className="mx-auto max-w-2xl sm:mx-0">
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
          Merchant portal
        </p>
        <h1 className="mt-1 font-display text-3xl text-charcoal-50 sm:text-4xl">
          Deal of the century
        </h1>
        <p className="mt-2 text-charcoal-400">
          Your Priority subscription landing page — pick a plan, unlock{" "}
          {DEAL_SLOT_LIMIT} slots, then publish deals that rank above scraped
          listings. Or skip the quota with Design Deals 4 U.
        </p>
      </div>

      {searchParams?.canceled ? (
        <div className="rounded-lg border border-charcoal-600 bg-charcoal-900/60 px-4 py-3 text-sm text-charcoal-300">
          Checkout canceled — no charge was made.
        </div>
      ) : null}

      <section className="space-y-4">
        <div className="flex flex-col flex-wrap items-center justify-between gap-3 sm:flex-row sm:items-end">
          <div className="max-w-2xl">
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
          <Badge variant="outline">No subscription yet</Badge>
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
          isSubscriber={isSubscriber}
          subscriptionPhase={phase}
        />
      </section>

      <div className="flex flex-wrap justify-center gap-3 sm:justify-start">
        <Button asChild size="lg" variant="outline">
          <Link href="/dashboard/profile">Your profile</Link>
        </Button>
      </div>
    </div>
  );
}
