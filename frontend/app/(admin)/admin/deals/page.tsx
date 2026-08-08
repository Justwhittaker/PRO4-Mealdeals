import Link from "next/link";
import {
  adminListDeals,
  adminListMerchants,
  type AdminDeal,
  type AdminMerchant,
} from "@/lib/admin-api";

function dealTitle(deal: AdminDeal): string {
  return deal.translations?.[0]?.title?.trim() || "Untitled deal";
}

export default async function AdminAllDealsPage() {
  const [dealsResult, merchantsResult] = await Promise.all([
    adminListDeals(),
    adminListMerchants(),
  ]);

  const merchantsById = new Map<string, AdminMerchant>();
  if (merchantsResult.ok) {
    for (const m of merchantsResult.data.results) {
      merchantsById.set(m.id, m);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-charcoal-50">All deals</h1>
        <p className="mt-2 text-charcoal-400">
          Cross-merchant deal inventory. Open a row to edit or delete.
        </p>
      </div>
      {!dealsResult.ok ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm">
          {dealsResult.error}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-charcoal-700">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-charcoal-700 bg-charcoal-900/40 text-charcoal-400">
              <tr>
                <th className="px-3 py-2 font-medium">Title</th>
                <th className="px-3 py-2 font-medium">Merchant</th>
                <th className="px-3 py-2 font-medium">Price</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {dealsResult.data.map((deal) => {
                const merchant = merchantsById.get(deal.merchant_id);
                return (
                  <tr key={deal.id} className="border-b border-charcoal-700/60">
                    <td className="px-3 py-2 text-charcoal-50">
                      {dealTitle(deal)}
                    </td>
                    <td className="px-3 py-2 text-charcoal-300">
                      <Link
                        href={`/admin/merchants/${deal.merchant_id}`}
                        className="hover:text-burgundy-600"
                      >
                        {merchant?.name || deal.merchant_id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-charcoal-300">
                      {deal.currency_code} {deal.deal_price}
                    </td>
                    <td className="px-3 py-2 text-charcoal-300">
                      {deal.is_active ? "active" : "inactive"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Link
                        href={`/admin/deals/${deal.id}/edit`}
                        className="text-xs text-burgundy-600 hover:underline"
                      >
                        Edit
                      </Link>
                    </td>
                  </tr>
                );
              })}
              {dealsResult.data.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-3 py-6 text-center text-charcoal-400"
                  >
                    No deals found.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
