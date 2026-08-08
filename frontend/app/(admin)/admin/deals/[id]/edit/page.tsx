import Link from "next/link";
import { notFound } from "next/navigation";
import { AdminDealForm } from "@/components/admin/AdminDealForm";
import { Button } from "@/components/ui/button";
import { adminGetDeal } from "@/lib/admin-api";

type Props = { params: Promise<{ id: string }> };

export default async function AdminEditDealPage({ params }: Props) {
  const { id } = await params;
  const deal = await adminGetDeal(id);
  if (!deal.ok) notFound();

  return (
    <div className="space-y-6">
      <div>
        <Button asChild variant="ghost" className="mb-2 h-8 px-0 text-xs">
          <Link href={`/admin/merchants/${deal.data.merchant_id}`}>
            ← Back to merchant
          </Link>
        </Button>
        <h1 className="font-display text-3xl text-charcoal-50">Edit deal</h1>
      </div>
      <AdminDealForm
        mode="edit"
        merchantId={deal.data.merchant_id}
        initial={deal.data}
      />
    </div>
  );
}
