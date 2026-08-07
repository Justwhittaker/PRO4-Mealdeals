import { Suspense } from "react";
import { cookies } from "next/headers";
import { LocationHeader } from "@/components/deals/LocationHeader";
import { CurrencySelector } from "@/components/deals/CurrencySelector";
import { RadiusSelector } from "@/components/deals/RadiusSelector";
import { AreaDealGrid } from "@/components/deals/AreaDealGrid";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { LocationDealsBar } from "@/components/geo/LocationDealsBar";
import { CitySearchBar } from "@/components/geo/CitySearchBar";
import { fetchDealsFeed } from "@/lib/api";
import {
  currencyForCountry,
  isCurrencyCode,
  type CurrencyCode,
} from "@/lib/currency";
import {
  LOCATION_COOKIE,
  LOCATION_SOURCE_COOKIE,
  cityDisplayLabel,
  countrySearchLabel,
  lookupCityCoords,
  parseLocationCookie,
  type LocationSource,
} from "@/lib/geo";
import {
  filterDealsByCategory,
  parseCategoryParam,
} from "@/lib/categories";
import {
  buildDealFeedParams,
  feedEmptyMessage,
} from "@/lib/deal-feed-query";
import { areaListingDeals } from "@/lib/priority";
import { parseFeedSort, parseRadiusMiles } from "@/lib/radius";

interface PageProps {
  params: { country: string; city: string };
  searchParams: {
    currency?: string;
    radius?: string;
    sort?: string;
    category?: string;
  };
}

export default async function CityPage({ params, searchParams }: PageProps) {
  const { country, city } = params;
  const localCurrency = currencyForCountry(country);
  const currency: CurrencyCode = isCurrencyCode(searchParams.currency)
    ? searchParams.currency.toUpperCase()
    : localCurrency;
  const radius = parseRadiusMiles(searchParams.radius);
  const sort = parseFeedSort(searchParams.sort);
  const category = parseCategoryParam(searchParams.category);
  const countryLabel = countrySearchLabel(country);
  const cityLabel = cityDisplayLabel(country, city);
  const hasCentroid = Boolean(lookupCityCoords(country, city));

  const jar = cookies();
  const pref = parseLocationCookie(jar.get(LOCATION_COOKIE)?.value);
  const source = (jar.get(LOCATION_SOURCE_COOKIE)?.value as
    | LocationSource
    | undefined) ?? "geo";
  const barTarget = pref?.citySlug === city
    ? pref
    : {
        countryCode:
          country.toLowerCase() === "gb" ? "uk" : country.toLowerCase(),
        countryLabel,
        citySlug: city,
        cityLabel,
      };

  const feed = await fetchDealsFeed(
    buildDealFeedParams({
      scope: "city",
      country,
      city,
      currency,
      sort,
      radius,
    }),
  );
  const deals = feed.ok
    ? filterDealsByCategory(areaListingDeals(feed.data), category)
    : [];
  const empty = feedEmptyMessage("city", cityLabel);

  return (
    <div className="min-h-screen bg-white">
      <LocationDealsBar target={barTarget} source={source} scope="city" />
      <main className="mx-auto max-w-[90rem] px-4 py-10 sm:px-6">
        <div className="mb-6">
          <CitySearchBar />
        </div>
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <LocationHeader
            country={country}
            city={city}
            subtitle={`HOT Deals near ${cityLabel}, ${countryLabel}${
              hasCentroid ? ` — within ${radius} miles` : ""
            }. ${deals.length} listing${deals.length === 1 ? "" : "s"}.`}
          />
          <div className="flex flex-col items-end gap-2">
            <Suspense fallback={null}>
              <RadiusSelector
                radius={radius}
                sort={sort}
                category={category}
                showRadius={hasCentroid}
              />
            </Suspense>
            <Suspense fallback={null}>
              <CurrencySelector value={currency} country={country} />
            </Suspense>
          </div>
        </div>

        {!feed.ok ? (
          <div className="mb-6 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            Couldn&apos;t load deals ({feed.error}). Start the API at{" "}
            <code className="text-citrus-300">NEXT_PUBLIC_API_URL</code> to
            populate this feed.
          </div>
        ) : null}

        <AreaDealGrid
          deals={deals}
          cityLabel={cityLabel}
          radiusMiles={hasCentroid ? radius : undefined}
          category={category}
          emptyMessage={empty.emptyMessage}
          emptyHint={empty.emptyHint}
        />
      </main>
      <SiteFooter />
    </div>
  );
}
