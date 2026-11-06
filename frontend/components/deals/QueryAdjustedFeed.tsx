"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AreaDealGrid } from "@/components/deals/AreaDealGrid";
import { FeedPagination } from "@/components/deals/FeedPagination";
import { parseCategoryParam } from "@/lib/categories";
import {
  currencyForCountry,
  isCurrencyCode,
  type CurrencyCode,
} from "@/lib/currency";
import {
  GEO_FEED_PAGE_SIZE,
  buildDealFeedParams,
  feedEmptyMessage,
  parseFeedPage,
  type DealFeedScope,
} from "@/lib/deal-feed-query";
import { fetchDealsFeedPage, type Deal } from "@/lib/api";
import { areaListingDeals } from "@/lib/priority";
import { parseFeedSort, parseRadiusMiles } from "@/lib/radius";
import { hasFeedFilterParams } from "@/lib/seo";

interface QueryAdjustedFeedProps {
  children: React.ReactNode;
  scope: DealFeedScope;
  country: string;
  city?: string;
  placeLabel: string;
  pathname: string;
  hasCentroid?: boolean;
}

/**
 * Canonical listing HTML is the `children` rendered on the server with no
 * query string. Filter and pagination query params refetch on the client so
 * the page itself does not read `searchParams` and can be cached.
 */
export function QueryAdjustedFeed({
  children,
  scope,
  country,
  city,
  placeLabel,
  pathname,
  hasCentroid = false,
}: QueryAdjustedFeedProps) {
  const searchParams = useSearchParams();
  const raw = {
    currency: searchParams.get("currency") ?? undefined,
    sort: searchParams.get("sort") ?? undefined,
    category: searchParams.get("category") ?? undefined,
    radius: searchParams.get("radius") ?? undefined,
    page: searchParams.get("page") ?? undefined,
  };
  const filtered = hasFeedFilterParams(raw);
  const queryKey = searchParams.toString();
  const [override, setOverride] = useState<{
    key: string;
    deals: Deal[];
    total: number;
    error: string | null;
  } | null>(null);

  useEffect(() => {
    if (!filtered) {
      setOverride(null);
      return;
    }
    let cancelled = false;
    const localCurrency = currencyForCountry(country);
    const currency: CurrencyCode =
      raw.currency && isCurrencyCode(raw.currency)
        ? (raw.currency.toUpperCase() as CurrencyCode)
        : localCurrency;
    const sort = parseFeedSort(raw.sort);
    const category = parseCategoryParam(raw.category);
    const radius = parseRadiusMiles(raw.radius);
    const page = parseFeedPage(raw.page);

    void fetchDealsFeedPage(
      buildDealFeedParams({
        scope,
        country,
        city,
        currency,
        sort,
        radius,
        category,
        page,
      }),
    ).then((result) => {
      if (cancelled) return;
      if (!result.ok) {
        setOverride({ key: queryKey, deals: [], total: 0, error: result.error });
        return;
      }
      setOverride({
        key: queryKey,
        deals: areaListingDeals(result.data.deals),
        total: result.data.total,
        error: null,
      });
    });

    return () => {
      cancelled = true;
    };
  }, [
    filtered,
    queryKey,
    scope,
    country,
    city,
    raw.currency,
    raw.sort,
    raw.category,
    raw.radius,
    raw.page,
  ]);

  const active = filtered && override && override.key === queryKey ? override : null;
  if (!active) return children;

  const empty = feedEmptyMessage(scope, placeLabel);
  const category = parseCategoryParam(raw.category);
  const radius = parseRadiusMiles(raw.radius);
  const page = parseFeedPage(raw.page);

  return (
    <>
      {active.error ? (
        <div className="mb-6 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Couldn&apos;t load this filtered view ({active.error}).
        </div>
      ) : null}
      <AreaDealGrid
        deals={active.deals}
        cityLabel={placeLabel}
        radiusMiles={scope === "city" && hasCentroid ? radius : undefined}
        category={category}
        emptyMessage={empty.emptyMessage}
        emptyHint={empty.emptyHint}
      />
      <FeedPagination
        page={page}
        pageSize={GEO_FEED_PAGE_SIZE}
        total={active.total}
        pathname={pathname}
        searchParams={raw}
      />
    </>
  );
}
