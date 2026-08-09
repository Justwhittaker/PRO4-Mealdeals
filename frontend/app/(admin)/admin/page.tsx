import { MerchantGeoBrowser } from "@/components/admin/MerchantGeoBrowser";
import { adminListDeals, adminListMerchants } from "@/lib/admin-api";

export default async function AdminHomePage() {
  const [merchantsResult, dealsResult] = await Promise.all([
    adminListMerchants(undefined, 5000),
    adminListDeals(undefined, 5000),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-charcoal-50">Merchants</h1>
        <p className="mt-2 text-charcoal-400">
          Country → city → merchant → deals. Preview opens the public deal or
          city feed; Manage opens the merchant profile.
        </p>
      </div>
      {!merchantsResult.ok ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-950">
          Could not load merchants ({merchantsResult.error}). Check{" "}
          <code className="text-xs">ADMIN_API_KEY</code> matches the API and the
          backend is running.
        </div>
      ) : (
        <MerchantGeoBrowser
          merchants={merchantsResult.data.results}
          deals={dealsResult.ok ? dealsResult.data : []}
        />
      )}
      {!dealsResult.ok ? (
        <p className="text-sm text-amber-800">
          Deals failed to load ({dealsResult.error}) — merchant deal previews
          may be incomplete.
        </p>
      ) : null}
    </div>
  );
}
