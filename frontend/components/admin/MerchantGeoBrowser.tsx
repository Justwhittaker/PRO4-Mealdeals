"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { AdminDeal, AdminMerchant } from "@/lib/admin-api";
import {
  cityDisplayName,
  countryDisplayName,
  groupByCountryCity,
  publicCityPath,
  publicDealPath,
  shareLabel,
  type GeoKeyedRow,
} from "@/lib/admin-geo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type MerchantRow = AdminMerchant & GeoKeyedRow;

function dealTitle(deal: AdminDeal): string {
  return deal.translations?.[0]?.title?.trim() || "Untitled deal";
}

export function MerchantGeoBrowser({
  merchants,
  deals,
}: {
  merchants: AdminMerchant[];
  deals: AdminDeal[];
}) {
  const [q, setQ] = useState("");

  const dealsByMerchant = useMemo(() => {
    const map = new Map<string, AdminDeal[]>();
    for (const deal of deals) {
      const bucket = map.get(deal.merchant_id);
      if (bucket) bucket.push(deal);
      else map.set(deal.merchant_id, [deal]);
    }
    return map;
  }, [deals]);

  const groups = useMemo(() => {
    const term = q.trim().toLowerCase();
    const rows: MerchantRow[] = merchants
      .filter((m) => {
        if (!term) return true;
        const merchantDeals = dealsByMerchant.get(m.id) ?? [];
        const dealHay = merchantDeals
          .map((d) => dealTitle(d))
          .join(" ")
          .toLowerCase();
        const hay =
          `${m.name} ${m.email ?? ""} ${m.location?.city ?? ""} ${m.location?.country_code ?? ""} ${dealHay}`.toLowerCase();
        return hay.includes(term);
      })
      .map((m) => ({
        ...m,
        countryCode: m.location?.country_code ?? "(unknown)",
        city: m.location?.city ?? "(unknown)",
      }));
    return groupByCountryCity(rows);
  }, [merchants, dealsByMerchant, q]);

  const viewTotal = groups.reduce((sum, g) => sum + g.total, 0);

  if (groups.length === 0) {
    return (
      <p className="text-sm text-charcoal-400">
        No merchants match.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <Input
        placeholder="Filter by merchant, deal, country, or city…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="max-w-md"
      />
      <div className="space-y-2">
        {groups.map((countryGroup) => (
          <details
            key={countryGroup.countryCode}
            className="rounded-lg border border-charcoal-700 bg-white"
            open={groups.length === 1}
          >
            <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm font-medium text-charcoal-50 [&::-webkit-details-marker]:hidden">
              <span>{countryDisplayName(countryGroup.countryCode)}</span>
              <span className="text-xs font-normal text-charcoal-400">
                {countryGroup.total.toLocaleString()} merchants ·{" "}
                {shareLabel(countryGroup.total, viewTotal)} of view
              </span>
            </summary>
            <div className="space-y-2 border-t border-charcoal-700/60 px-3 py-3">
              {countryGroup.cities.map((cityGroup) => (
                <details
                  key={`${countryGroup.countryCode}-${cityGroup.city}`}
                  className="rounded-md border border-charcoal-700/60"
                >
                  <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm text-charcoal-100 [&::-webkit-details-marker]:hidden">
                    <span>{cityDisplayName(cityGroup.city)}</span>
                    <span className="text-xs text-charcoal-400">
                      {cityGroup.items.length.toLocaleString()} ·{" "}
                      {shareLabel(cityGroup.items.length, countryGroup.total)} of{" "}
                      {countryDisplayName(countryGroup.countryCode)}
                    </span>
                  </summary>
                  <div className="space-y-2 border-t border-charcoal-700/60 p-3">
                    {cityGroup.items.map((merchant) => {
                      const merchantDeals = dealsByMerchant.get(merchant.id) ?? [];
                      const hasLocation =
                        merchant.location?.country_code && merchant.location?.city;
                      return (
                        <details
                          key={merchant.id}
                          className="rounded-md border border-charcoal-700/40 bg-charcoal-900/5"
                        >
                          <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm [&::-webkit-details-marker]:hidden">
                            <span className="font-medium text-charcoal-50">
                              {merchant.name}
                            </span>
                            <span className="text-xs text-charcoal-400">
                              {merchantDeals.length} deal
                              {merchantDeals.length === 1 ? "" : "s"} ·{" "}
                              {merchant.is_subscriber
                                ? merchant.tier_level
                                : "free / scraped"}
                            </span>
                          </summary>
                          <div className="space-y-3 border-t border-charcoal-700/40 px-3 py-3">
                            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-charcoal-400">
                              <span>{merchant.email || "No email"}</span>
                              <div className="flex flex-wrap gap-2">
                                {hasLocation ? (
                                  <Button
                                    asChild
                                    variant="outline"
                                    className="h-8 px-2 text-xs"
                                  >
                                    <Link
                                      href={publicCityPath(
                                        merchant.location!.country_code,
                                        merchant.location!.city,
                                      )}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                    >
                                      Preview city
                                    </Link>
                                  </Button>
                                ) : null}
                                <Button
                                  asChild
                                  variant="outline"
                                  className="h-8 px-2 text-xs"
                                >
                                  <Link href={`/admin/merchants/${merchant.id}`}>
                                    Manage
                                  </Link>
                                </Button>
                              </div>
                            </div>
                            {merchantDeals.length > 0 ? (
                              <div className="overflow-x-auto rounded-md border border-charcoal-700/60">
                                <table className="min-w-full text-left text-sm">
                                  <thead className="border-b border-charcoal-700/60 bg-charcoal-900/20 text-charcoal-400">
                                    <tr>
                                      <th className="px-3 py-2 font-medium">
                                        Deal
                                      </th>
                                      <th className="px-3 py-2 font-medium">
                                        Price
                                      </th>
                                      <th className="px-3 py-2 font-medium">
                                        Status
                                      </th>
                                      <th className="px-3 py-2 font-medium" />
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {merchantDeals.map((deal) => (
                                      <tr
                                        key={deal.id}
                                        className="border-b border-charcoal-700/30 last:border-0"
                                      >
                                        <td className="px-3 py-2 text-charcoal-50">
                                          {dealTitle(deal)}
                                        </td>
                                        <td className="px-3 py-2 text-charcoal-300">
                                          {deal.currency_code} {deal.deal_price}
                                        </td>
                                        <td className="px-3 py-2 text-charcoal-300">
                                          {deal.is_active ? "active" : "inactive"}
                                        </td>
                                        <td className="px-3 py-2">
                                          <div className="flex flex-wrap justify-end gap-2">
                                            {hasLocation ? (
                                              <Button
                                                asChild
                                                variant="outline"
                                                className="h-8 px-2 text-xs"
                                              >
                                                <Link
                                                  href={publicDealPath(
                                                    merchant.location!
                                                      .country_code,
                                                    merchant.location!.city,
                                                    deal.id,
                                                  )}
                                                  target="_blank"
                                                  rel="noopener noreferrer"
                                                >
                                                  Preview
                                                </Link>
                                              </Button>
                                            ) : null}
                                            <Button
                                              asChild
                                              variant="outline"
                                              className="h-8 px-2 text-xs"
                                            >
                                              <Link
                                                href={`/admin/deals/${deal.id}/edit`}
                                              >
                                                Edit
                                              </Link>
                                            </Button>
                                          </div>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            ) : (
                              <p className="text-xs text-charcoal-400">
                                No deals for this merchant.
                              </p>
                            )}
                          </div>
                        </details>
                      );
                    })}
                  </div>
                </details>
              ))}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
