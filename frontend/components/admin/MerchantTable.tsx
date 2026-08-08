"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AdminMerchant } from "@/lib/admin-api";

export function MerchantTable({
  initialMerchants,
}: {
  initialMerchants: AdminMerchant[];
}) {
  const [q, setQ] = useState("");
  const router = useRouter();

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return initialMerchants;
    return initialMerchants.filter((m) => {
      const hay = `${m.name} ${m.email ?? ""} ${m.location?.city ?? ""}`.toLowerCase();
      return hay.includes(term);
    });
  }, [initialMerchants, q]);

  return (
    <div className="space-y-4">
      <Input
        placeholder="Filter by name, email, or city…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="max-w-md"
      />
      <div className="overflow-x-auto rounded-lg border border-charcoal-700">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-charcoal-700 bg-charcoal-900/40 text-charcoal-400">
            <tr>
              <th className="px-3 py-2 font-medium">Merchant</th>
              <th className="px-3 py-2 font-medium">Email</th>
              <th className="px-3 py-2 font-medium">Location</th>
              <th className="px-3 py-2 font-medium">Plan</th>
              <th className="px-3 py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((m) => (
              <tr key={m.id} className="border-b border-charcoal-700/60">
                <td className="px-3 py-2 text-charcoal-50">{m.name}</td>
                <td className="px-3 py-2 text-charcoal-300">{m.email || "—"}</td>
                <td className="px-3 py-2 text-charcoal-300">
                  {m.location
                    ? `${m.location.city}, ${m.location.country_code}`
                    : "—"}
                </td>
                <td className="px-3 py-2 text-charcoal-300">
                  {m.is_subscriber ? m.tier_level : "free / scraped"}
                </td>
                <td className="px-3 py-2 text-right">
                  <Button asChild variant="outline" className="h-8 px-3 text-xs">
                    <Link href={`/admin/merchants/${m.id}`}>Manage</Link>
                  </Button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-charcoal-400">
                  No merchants match.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <Button type="button" variant="ghost" className="text-xs" onClick={() => router.refresh()}>
        Refresh
      </Button>
    </div>
  );
}
