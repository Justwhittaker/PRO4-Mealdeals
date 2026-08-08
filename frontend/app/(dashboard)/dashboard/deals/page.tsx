import Link from "next/link";
import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { authOptions } from "@/lib/auth";
import { fetchDealHistory } from "@/lib/api";
import { DealHistory } from "./deal-history";

export default async function MerchantDealsPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/dashboard");

  const merchantId = session.user.id;
  const history = await fetchDealHistory(merchantId);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl text-charcoal-50">Your deals</h1>
          <p className="mt-2 text-charcoal-400">
            Live Priority slots plus saved drafts — create, preview, activate,
            deactivate to free a slot, or delete when you no longer need a deal.
          </p>
        </div>
        <Button asChild>
          <Link href="/dashboard/deals/new">Create deal</Link>
        </Button>
      </div>

      {!history.ok ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Couldn&apos;t load history ({history.error}). Link your login to a
          merchant profile id first.
        </div>
      ) : (
        <DealHistory
          merchantId={merchantId}
          initialDeals={history.data.results}
          openSlots={history.data.open_slots}
          activeCount={history.data.active_count}
        />
      )}
    </div>
  );
}
