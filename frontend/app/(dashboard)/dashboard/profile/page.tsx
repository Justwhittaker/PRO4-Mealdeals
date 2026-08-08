import Link from "next/link";
import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { syncMerchantPriorityFromStripe } from "@/actions/stripe";
import { LogoutButton } from "@/components/auth/LogoutButton";
import { CustomerPortalCard } from "@/components/merchant/CustomerPortalCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { authOptions } from "@/lib/auth";
import { fetchMerchantProfile } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import { DESIGN_SPECIAL } from "@/lib/stripe";
import { ProfileForm } from "./profile-form";

export default async function ProfilePage({
  searchParams,
}: {
  searchParams?: { success?: string; plan?: string };
}) {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/dashboard");

  const merchantId = session.user.id;
  let profile = await fetchMerchantProfile(merchantId);

  // After Priority checkout, activate from Stripe if the webhook lagged.
  if (searchParams?.success === "1") {
    const sync = await syncMerchantPriorityFromStripe(merchantId);
    if (sync.synced) {
      profile = await fetchMerchantProfile(merchantId);
    }
  }

  const isSubscriber = profile.ok ? profile.data.is_subscriber : false;
  const openSlots = profile.ok ? profile.data.open_slots : 0;
  const stripeCustomerId = profile.ok
    ? profile.data.stripe_customer_id ?? null
    : null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl text-charcoal-50">Profile</h1>
        <p className="mt-2 text-charcoal-400">
          Your venue identity, subscription, and deal history live here so you
          can repost past offers into open Priority slots.
        </p>
      </div>

      {searchParams?.success ? (
        <div className="rounded-lg border border-burgundy-200 bg-burgundy-50 px-4 py-3 text-sm text-charcoal-200">
          {isSubscriber
            ? searchParams.plan === "trial"
              ? "You're on Priority — first month free on your monthly plan. Billing starts after 30 days unless you cancel."
              : searchParams.plan === "promo"
                ? "You're on Priority — discounted three months are active, then monthly continues."
                : "Priority subscription is active."
            : "Checkout completed — activating your Priority monthly plan… refresh if slots don’t appear yet."}
        </div>
      ) : null}

      {!profile.ok ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Couldn&apos;t load profile ({profile.error}). Start the API at{" "}
          <code className="text-citrus-300">NEXT_PUBLIC_API_URL</code> — signing
          in creates/links a merchant profile automatically.
        </div>
      ) : (
        <ProfileForm merchantId={merchantId} initial={profile.data} />
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Session</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-sm text-charcoal-400">
            Signed in as{" "}
            <span className="text-charcoal-100">
              {session.user?.email ?? session.user?.name ?? "merchant"}
            </span>
          </p>
          <LogoutButton label="Log out of Dine A Deal" />
        </CardContent>
      </Card>

      <section className="space-y-4">
        <CustomerPortalCard stripeCustomerId={stripeCustomerId} />

        <div className="grid gap-4 lg:grid-cols-2">
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
                  Choose a subscription on{" "}
                  <Link
                    href="/dashboard"
                    className="font-medium text-burgundy-600 underline-offset-2 hover:underline"
                  >
                    Deal of the century
                  </Link>{" "}
                  before you can add a new Priority deal.
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                {isSubscriber ? (
                  <Button asChild>
                    <Link href="/dashboard/deals/new">
                      Create a Priority deal
                    </Link>
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
                {formatMoney(DESIGN_SPECIAL.amount, DESIGN_SPECIAL.currency)}{" "}
                per deal
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
        </div>
      </section>
    </div>
  );
}
