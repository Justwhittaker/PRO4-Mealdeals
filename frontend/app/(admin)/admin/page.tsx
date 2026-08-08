import { adminListMerchants } from "@/lib/admin-api";
import { MerchantTable } from "@/components/admin/MerchantTable";

export default async function AdminHomePage() {
  const result = await adminListMerchants();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-charcoal-50">Merchants</h1>
        <p className="mt-2 text-charcoal-400">
          Load customer / merchant profiles, edit details, manage deals, or remove
          accounts from the website.
        </p>
      </div>
      {!result.ok ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-950">
          Could not load merchants ({result.error}). Check{" "}
          <code className="text-xs">ADMIN_API_KEY</code> matches the API and the
          backend is running.
        </div>
      ) : (
        <MerchantTable initialMerchants={result.data.results} />
      )}
    </div>
  );
}
