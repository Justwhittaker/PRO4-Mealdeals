import Link from "next/link";
import { notFound } from "next/navigation";
import { MerchantAdminPanel } from "@/components/admin/MerchantAdminPanel";
import { Button } from "@/components/ui/button";
import {
  adminGetMerchant,
  adminListMerchantDeals,
} from "@/lib/admin-api";

type Props = { params: Promise<{ id: string }> };

export default async function AdminMerchantPage({ params }: Props) {
  const { id } = await params;
  const [merchant, deals] = await Promise.all([
    adminGetMerchant(id),
    adminListMerchantDeals(id),
  ]);

  if (!merchant.ok) notFound();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Button asChild variant="ghost" className="mb-2 h-8 px-0 text-xs">
            <Link href="/admin">← All merchants</Link>
          </Button>
          <h1 className="font-display text-3xl text-charcoal-50">
            {merchant.data.name}
          </h1>
          <p className="mt-1 text-sm text-charcoal-400">
            {merchant.data.email || "No email"} ·{" "}
            {merchant.data.active_deal_count ?? 0} active /{" "}
            {merchant.data.total_deal_count ?? 0} total deals
          </p>
        </div>
      </div>
      <MerchantAdminPanel
        merchant={merchant.data}
        deals={deals.ok ? deals.data : []}
      />
      {!deals.ok ? (
        <p className="text-sm text-burgundy-600">
          Deals failed to load: {deals.error}
        </p>
      ) : null}
    </div>
  );
}
