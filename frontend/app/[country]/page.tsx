import Link from "next/link";
import { Suspense } from "react";
import { LocationHeader } from "@/components/deals/LocationHeader";
import { CurrencySelector } from "@/components/deals/CurrencySelector";
import { RadiusSelector } from "@/components/deals/RadiusSelector";
import { AreaDealGrid } from "@/components/deals/AreaDealGrid";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { NewsletterDealGate } from "@/components/newsletter/NewsletterDealGate";
import { CitySearchBar } from "@/components/geo/CitySearchBar";
import { fetchDealsFeed } from "@/lib/api";
import {
  currencyForCountry,
  isCurrencyCode,
  type CurrencyCode,
} from "@/lib/currency";
import {
  filterDealsByCategory,
  parseCategoryParam,
} from "@/lib/categories";
import {
  POPULAR_CITIES,
  countrySearchLabel,
} from "@/lib/geo";
import {
  buildDealFeedParams,
  feedEmptyMessage,
} from "@/lib/deal-feed-query";
import { areaListingDeals } from "@/lib/priority";
import { parseFeedSort, parseRadiusMiles } from "@/lib/radius";

interface PageProps {
  params: { country: string };
  searchParams: {
    currency?: string;
    sort?: string;
    category?: string;
    radius?: string;
  };
}

export default async function CountryPage({ params, searchParams }: PageProps) {
  const { country } = params;
  const localCurrency = currencyForCountry(country);
  const currency: CurrencyCode = isCurrencyCode(searchParams.currency)
    ? searchParams.currency.toUpperCase()
    : localCurrency;
  const sort = parseFeedSort(searchParams.sort);
  const category = parseCategoryParam(searchParams.category);
  const radius = parseRadiusMiles(searchParams.radius);
  const countryLabel = countrySearchLabel(country);

  const feed = await fetchDealsFeed(
    buildDealFeedParams({
      scope: "country",
      country,
      currency,
      sort,
    }),
  );
  const deals = feed.ok
    ? filterDealsByCategory(areaListingDeals(feed.data), category)
    : [];
  const countrySlug =
    country.toLowerCase() === "gb" ? "uk" : country.toLowerCase();
  const cities = POPULAR_CITIES.filter((c) => c.country === countrySlug);
  const empty = feedEmptyMessage("country", countryLabel);

  return (
    <div className="min-h-screen bg-white">
      <main className="mx-auto max-w-[90rem] px-4 py-10 sm:px-6">
        <div className="mb-6">
          <CitySearchBar />
        </div>
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <LocationHeader
            country={country}
            subtitle={`HOT Deals across ${countryLabel} — all categories. ${deals.length} listings.`}
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

        {cities.length > 0 ? (
          <div className="mb-10 flex flex-wrap gap-2">
            {cities.map((c) => (
              <Link
                key={c.city}
                href={`/${country}/${c.city}?currency=${localCurrency}`}
                className="rounded-md border border-charcoal-700 bg-white px-3 py-1.5 text-sm text-charcoal-200 transition hover:border-burgundy-300 hover:text-burgundy-600"
              >
                {c.label}
              </Link>
            ))}
          </div>
        ) : null}

        <NewsletterDealGate>
          {!feed.ok ? (
            <div className="mb-6 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              Couldn&apos;t reach the deals API ({feed.error}). Showing an empty
              feed until the backend is available.
            </div>
          ) : null}

          <AreaDealGrid
            deals={deals}
            cityLabel={countryLabel}
            category={category}
            emptyMessage={empty.emptyMessage}
            emptyHint={empty.emptyHint}
          />
        </NewsletterDealGate>
      </main>
      <SiteFooter />
    </div>
  );
}
