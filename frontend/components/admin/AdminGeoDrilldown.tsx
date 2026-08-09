"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import {
  cityDisplayName,
  countryDisplayName,
  shareLabel,
  type GeoCountryGroup,
} from "@/lib/admin-geo";
import { Button } from "@/components/ui/button";

type AdminGeoDrilldownProps<T> = {
  groups: GeoCountryGroup<T>[];
  unit: string;
  renderRow: (item: T) => {
    key: string;
    primary: ReactNode;
    secondary?: ReactNode;
    previewHref?: string;
    manageHref?: string;
  };
  emptyMessage?: string;
};

export function AdminGeoDrilldown<T>({
  groups,
  unit,
  renderRow,
  emptyMessage = "Nothing to show.",
}: AdminGeoDrilldownProps<T>) {
  const viewTotal = groups.reduce((sum, g) => sum + g.total, 0);

  if (groups.length === 0) {
    return <p className="text-sm text-charcoal-400">{emptyMessage}</p>;
  }

  return (
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
              {countryGroup.total.toLocaleString()} {unit} ·{" "}
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
                <div className="overflow-x-auto border-t border-charcoal-700/60">
                  <table className="min-w-full text-left text-sm">
                    <tbody>
                      {cityGroup.items.map((item) => {
                        const row = renderRow(item);
                        return (
                          <tr
                            key={row.key}
                            className="border-b border-charcoal-700/40 last:border-0"
                          >
                            <td className="px-3 py-2 text-charcoal-50">
                              {row.primary}
                              {row.secondary ? (
                                <div className="text-xs text-charcoal-400">
                                  {row.secondary}
                                </div>
                              ) : null}
                            </td>
                            <td className="px-3 py-2 text-right">
                              <div className="flex flex-wrap justify-end gap-2">
                                {row.previewHref ? (
                                  <Button
                                    asChild
                                    variant="outline"
                                    className="h-8 px-2 text-xs"
                                  >
                                    <Link
                                      href={row.previewHref}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                    >
                                      Preview
                                    </Link>
                                  </Button>
                                ) : null}
                                {row.manageHref ? (
                                  <Button
                                    asChild
                                    variant="outline"
                                    className="h-8 px-2 text-xs"
                                  >
                                    <Link href={row.manageHref}>Manage</Link>
                                  </Button>
                                ) : null}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </details>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}
