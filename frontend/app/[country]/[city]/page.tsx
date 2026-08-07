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
  countrySearchLabel,
  parseLocationCookie,
  type LocationSource,
} from "@/lib/geo";
import {
  filterDealsByCategory,
  parseCategoryParam,
} from "@/lib/categories";
import { areaListingDeals } from "@/lib/priority";
import { parseFeedSort, parseRadiusMiles } from "@/lib/radius";

/** Request enough rows for full country listings (backend max 10000). */
const GEO_FEED_LIMIT = 10000;

interface PageProps {
  params: { country: string; city: string };
  searchParams: {
    currency?: string;
    radius?: string;
    sort?: string;
    category?: string;
  };
}

function titleCase(slug: string) {
  return slug
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
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
  const cityLabel = titleCase(city);

  const jar = cookies();
  const pref = parseLocationCookie(jar.get(LOCATION_COOKIE)?.value);
  const source = (jar.get(LOCATION_SOURCE_COOKIE)?.value as
    | LocationSource
    | undefined) ?? "geo";
  const barTarget = pref ?? {
    countryCode: country.toLowerCase() === "gb" ? "uk" : country.toLowerCase(),
    countryLabel,
    citySlug: city,
    cityLabel,
  };

  // Full country listing for the selected geo — not a single-city radius slice.
  const feed = await fetchDealsFeed({
    country,
    currency,
    limit: GEO_FEED_LIMIT,
    sort,
  });
  const deals = feed.ok
    ? filterDealsByCategory(areaListingDeals(feed.data), category)
    : [];

  return (
    <div className="min-h-screen bg-white">
      <LocationDealsBar target={barTarget} source={source} scope="country" />
      <main className="mx-auto max-w-[90rem] px-4 py-10 sm:px-6">
        <div className="mb-6">
          <CitySearchBar />
        </div>
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <LocationHeader
            country={country}
            city={city}
            subtitle={`HOT Deals across ${countryLabel} — all categories (hub: ${cityLabel}). ${deals.length} listings.`}
          />
          <div className="flex flex-col items-end gap-2">
            <Suspense fallback={null}>
              <RadiusSelector
                radius={radius}
                sort={sort}
                category={category}
                showRadius={false}
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
          cityLabel={countryLabel}
          category={category}
          emptyMessage={`No deals listed across ${countryLabel} yet.`}
          emptyHint="Search another country or check back soon."
        />
      </main>
      <SiteFooter />
    </div>
  );
}
