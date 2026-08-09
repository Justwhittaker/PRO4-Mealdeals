import { AdminDealsGeoBrowser } from "@/components/admin/AdminDealsGeoBrowser";
import {
  adminListDeals,
  adminListMerchants,
} from "@/lib/admin-api";

export default async function AdminAllDealsPage() {
  const [dealsResult, merchantsResult] = await Promise.all([
    adminListDeals(undefined, 5000),
    adminListMerchants(undefined, 5000),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-charcoal-50">All deals</h1>
        <p className="mt-2 text-charcoal-400">
          Browse by country and city. Preview opens the public deal page; Manage
          opens the staff editor.
        </p>
      </div>
      {!dealsResult.ok ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm">
          {dealsResult.error}
        </div>
      ) : (
        <AdminDealsGeoBrowser
          deals={dealsResult.data}
          merchants={merchantsResult.ok ? merchantsResult.data.results : []}
        />
      )}
    </div>
  );
}
