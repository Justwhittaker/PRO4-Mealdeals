import Link from "next/link";
import { notFound } from "next/navigation";
import { AdminDealForm } from "@/components/admin/AdminDealForm";
import { Button } from "@/components/ui/button";
import { adminGetMerchant } from "@/lib/admin-api";

type Props = { params: Promise<{ id: string }> };

export default async function AdminNewDealPage({ params }: Props) {
  const { id } = await params;
  const merchant = await adminGetMerchant(id);
  if (!merchant.ok) notFound();

  return (
    <div className="space-y-6">
      <div>
        <Button asChild variant="ghost" className="mb-2 h-8 px-0 text-xs">
          <Link href={`/admin/merchants/${id}`}>← {merchant.data.name}</Link>
        </Button>
        <h1 className="font-display text-3xl text-charcoal-50">Add deal</h1>
        <p className="mt-2 text-charcoal-400">
          Staff-created deals are slot-exempt and appear on the public site when
          active.
        </p>
      </div>
      <AdminDealForm mode="create" merchantId={id} />
    </div>
  );
}
