import Link from "next/link";
import { getServerSession } from "next-auth";
import { notFound, redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { authOptions } from "@/lib/auth";
import { fetchMerchantDeal, fetchMerchantProfile } from "@/lib/api";
import { NewDealForm } from "../../new/new-deal-form";

interface EditDealPageProps {
  params: { id: string };
}

export default async function EditDealPage({ params }: EditDealPageProps) {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/dashboard");

  const { id } = params;
  const merchantId = session.user.id;
  const [profile, deal] = await Promise.all([
    fetchMerchantProfile(merchantId),
    fetchMerchantDeal(id),
  ]);

  if (!deal.ok) notFound();
  if (deal.data.merchant_id !== merchantId) {
    return (
      <div className="space-y-4">
        <h1 className="font-display text-3xl text-charcoal-50">Edit deal</h1>
        <p className="text-amber-200">This deal does not belong to your account.</p>
        <Button asChild>
          <Link href="/dashboard/deals">Back to your deals</Link>
        </Button>
      </div>
    );
  }

  const openSlots = profile.ok ? profile.data.open_slots : 0;
  const isSubscriber = profile.ok ? profile.data.is_subscriber : false;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl text-charcoal-50">Edit deal</h1>
          <p className="mt-2 max-w-xl text-charcoal-400">
            Update the offer, photo, items, or price. Deactivate from Your deals
            if you need to free a Priority slot.
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/dashboard/deals">Back to deals</Link>
        </Button>
      </div>
      <NewDealForm
        merchantId={merchantId}
        openSlots={openSlots}
        isSubscriber={isSubscriber}
        mode="edit"
        dealId={id}
        initialDeal={deal.data}
      />
    </div>
  );
}
