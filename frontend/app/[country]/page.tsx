import Link from "next/link";
import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { LocationHeader } from "@/components/deals/LocationHeader";
import { CurrencySelector } from "@/components/deals/CurrencySelector";
import { RadiusSelector } from "@/components/deals/RadiusSelector";
import { AreaDealGrid } from "@/components/deals/AreaDealGrid";
import { FeedPagination } from "@/components/deals/FeedPagination";
import { PublisherExplainer } from "@/components/landing/PublisherExplainer";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { NewsletterDealGate } from "@/components/newsletter/NewsletterDealGate";
import { CitySearchBar } from "@/components/geo/CitySearchBar";
import { fetchDealsFeed, fetchDealsFeedPage } from "@/lib/api";
import {
  currencyForCountry,
  isCurrencyCode,
  type CurrencyCode,
} from "@/lib/currency";
import { parseCategoryParam } from "@/lib/categories";
import {
  POPULAR_CITIES,
  countrySearchLabel,
} from "@/lib/geo";
import {
  GEO_FEED_PAGE_SIZE,
  buildDealFeedParams,
  feedEmptyMessage,
  parseFeedPage,
} from "@/lib/deal-feed-query";
import { areaListingDeals } from "@/lib/priority";
import { parseFeedSort, parseRadiusMiles } from "@/lib/radius";
import { JsonLd } from "@/components/seo/JsonLd";
import {
  breadcrumbJsonLd,
  countryListingMetadata,
  hasFeedFilterParams,
  isIndexableCountrySlug,
  itemListJsonLd,
  listingPath,
  withFeaturedDealDescription,
  withNoIndexFollow,
} from "@/lib/seo";
import { BRAND_NAME } from "@/lib/brand";

interface PageProps {
  params: { country: string };
  searchParams: {
    currency?: string;
    sort?: string;
    category?: string;
    radius?: string;
    page?: string;
  };
}

export async function generateMetadata({
  params,
  searchParams,
}: PageProps): Promise<Metadata> {
  if (!isIndexableCountrySlug(params.country)) {
    return { robots: { index: false, follow: false } };
  }
  const feed = await fetchDealsFeed(
    buildDealFeedParams({
      scope: "country",
      country: params.country,
      currency: currencyForCountry(params.country),
      sort: "score",
      page: 1,
    }),
  );
  let meta = withFeaturedDealDescription(
    countryListingMetadata(params.country),
    feed.ok ? feed.data : [],
  );
  if (hasFeedFilterParams(searchParams)) {
    meta = withNoIndexFollow(meta);
  }
  return meta;
}

export default async function CountryPage({ params, searchParams }: PageProps) {
  if (!isIndexableCountrySlug(params.country)) notFound();
  const { country } = params;
  const localCurrency = currencyForCountry(country);
  const currency: CurrencyCode = isCurrencyCode(searchParams.currency)
    ? searchParams.currency.toUpperCase()
    : localCurrency;
  const sort = parseFeedSort(searchParams.sort);
  const category = parseCategoryParam(searchParams.category);
  const radius = parseRadiusMiles(searchParams.radius);
  const page = parseFeedPage(searchParams.page);
  const countryLabel = countrySearchLabel(country);
  const listingHref = listingPath(country);

  const feed = await fetchDealsFeedPage(
    buildDealFeedParams({
      scope: "country",
      country,
      currency,
      sort,
      category,
      page,
    }),
  );
  const deals = feed.ok ? areaListingDeals(feed.data.deals) : [];
  const total = feed.ok ? feed.data.total : 0;
  const countrySlug =
    country.toLowerCase() === "gb" ? "uk" : country.toLowerCase();
  const cities = POPULAR_CITIES.filter((c) => c.country === countrySlug);
  const empty = feedEmptyMessage("country", countryLabel);
  const preservedParams = {
    currency: searchParams.currency,
    sort: searchParams.sort,
    category: searchParams.category,
    radius: searchParams.radius,
  };

  return (
    <div className="min-h-screen bg-white">
      <main className="mx-auto max-w-[90rem] px-4 py-10 sm:px-6">
        <div className="mb-6">
          <CitySearchBar />
        </div>
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <LocationHeader
            country={country}
            subtitle={`HOT Deals across ${countryLabel} — all categories. ${total} listing${
              total === 1 ? "" : "s"
            }.`}
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

        <PublisherExplainer areaLabel={countryLabel} />

        <JsonLd
          data={[
            breadcrumbJsonLd([
              { name: BRAND_NAME, path: "/" },
              { name: countryLabel, path: listingHref },
            ]),
            itemListJsonLd(`Dining deals across ${countryLabel}`, deals),
          ]}
        />

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

          <FeedPagination
            page={page}
            pageSize={GEO_FEED_PAGE_SIZE}
            total={total}
            pathname={listingHref}
            searchParams={preservedParams}
          />
        </NewsletterDealGate>
      </main>
      <SiteFooter />
    </div>
  );
}
