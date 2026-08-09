"use client";

import { useMemo, useState } from "react";
import type { AdminDeal, AdminMerchant } from "@/lib/admin-api";
import {
  groupByCountryCity,
  publicDealPath,
  type GeoKeyedRow,
} from "@/lib/admin-geo";
import { AdminGeoDrilldown } from "@/components/admin/AdminGeoDrilldown";
import { Input } from "@/components/ui/input";

type DealRow = AdminDeal &
  GeoKeyedRow & {
    merchantName: string;
  };

function dealTitle(deal: AdminDeal): string {
  return deal.translations?.[0]?.title?.trim() || "Untitled deal";
}

export function AdminDealsGeoBrowser({
  deals,
  merchants,
}: {
  deals: AdminDeal[];
  merchants: AdminMerchant[];
}) {
  const [q, setQ] = useState("");

  const merchantsById = useMemo(() => {
    const map = new Map<string, AdminMerchant>();
    for (const m of merchants) map.set(m.id, m);
    return map;
  }, [merchants]);

  const groups = useMemo(() => {
    const term = q.trim().toLowerCase();
    const rows: DealRow[] = deals
      .map((deal) => {
        const merchant = merchantsById.get(deal.merchant_id);
        return {
          ...deal,
          merchantName: merchant?.name ?? deal.merchant_id.slice(0, 8),
          countryCode: merchant?.location?.country_code ?? "(unknown)",
          city: merchant?.location?.city ?? "(unknown)",
        };
      })
      .filter((row) => {
        if (!term) return true;
        const hay = `${dealTitle(row)} ${row.merchantName} ${row.countryCode} ${row.city}`.toLowerCase();
        return hay.includes(term);
      });
    return groupByCountryCity(rows);
  }, [deals, merchantsById, q]);

  return (
    <div className="space-y-4">
      <Input
        placeholder="Filter by deal, merchant, country, or city…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="max-w-md"
      />
      <AdminGeoDrilldown
        groups={groups}
        unit="deals"
        emptyMessage="No deals match."
        renderRow={(deal) => ({
          key: deal.id,
          primary: dealTitle(deal),
          secondary: [
            deal.merchantName,
            `${deal.currency_code} ${deal.deal_price}`,
            deal.is_active ? "active" : "inactive",
          ].join(" · "),
          previewHref:
            deal.countryCode && deal.city && deal.countryCode !== "(unknown)"
              ? publicDealPath(deal.countryCode, deal.city, deal.id)
              : undefined,
          manageHref: `/admin/deals/${deal.id}/edit`,
        })}
      />
    </div>
  );
}
