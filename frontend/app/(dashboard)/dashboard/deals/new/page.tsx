import Link from "next/link";
import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { authOptions } from "@/lib/auth";
import { fetchMerchantProfile } from "@/lib/api";
import { NewDealForm } from "./new-deal-form";

function slugifyCity(city: string): string {
  return city.trim().toLowerCase().replace(/\s+/g, "-");
}

export default async function NewDealPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/dashboard");

  const merchantId = session.user.id;
  const profile = await fetchMerchantProfile(merchantId);
  const isSubscriber = profile.ok ? profile.data.is_subscriber : false;
  const openSlots = profile.ok ? profile.data.open_slots : 0;
  const restaurantName = profile.ok ? profile.data.name : "Your restaurant";
  const logoUrl = profile.ok ? profile.data.logo_url ?? null : null;
  const countryCode = profile.ok
    ? (profile.data.location?.country_code || "ie").toLowerCase()
    : "ie";
  const citySlug = profile.ok
    ? slugifyCity(profile.data.location?.city || "city")
    : "city";

  if (!isSubscriber) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-3xl text-charcoal-50">New deal</h1>
          <p className="mt-2 max-w-xl text-charcoal-400">
            You need an active Priority subscription before you can add a deal.
          </p>
        </div>
        <div className="rounded-lg border border-burgundy-200 bg-burgundy-50 px-4 py-4 text-sm text-charcoal-200">
          <p>
            Choose a plan on{" "}
            <strong className="text-charcoal-50">Deal of the century</strong> —
            free first month (card required) or pay now for 50% off three months.
          </p>
          <Button asChild className="mt-4">
            <Link href="/dashboard">Choose a subscription</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-charcoal-50">New deal</h1>
        <p className="mt-2 max-w-xl text-charcoal-400">
          Build a deal and watch the value calculator update in real time —
          market value vs your offer price.
        </p>
      </div>
      <NewDealForm
        merchantId={merchantId}
        openSlots={openSlots}
        isSubscriber={isSubscriber}
        restaurantName={restaurantName}
        logoUrl={logoUrl}
        countryCode={countryCode}
        citySlug={citySlug}
      />
    </div>
  );
}
