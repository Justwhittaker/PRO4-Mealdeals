import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { cookies } from "next/headers";
import { LocationHeader } from "@/components/deals/LocationHeader";
import { CurrencySelector } from "@/components/deals/CurrencySelector";
import { RadiusSelector } from "@/components/deals/RadiusSelector";
import { AreaDealGrid } from "@/components/deals/AreaDealGrid";
import { FeedPagination } from "@/components/deals/FeedPagination";
import { PublisherExplainer } from "@/components/landing/PublisherExplainer";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { NewsletterDealGate } from "@/components/newsletter/NewsletterDealGate";
import { LocationDealsBar } from "@/components/geo/LocationDealsBar";
import { CitySearchBar } from "@/components/geo/CitySearchBar";
import { fetchDealsFeed, fetchDealsFeedPage } from "@/lib/api";
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
  isPlaceholderCitySlug,
  lookupCityCoords,
  parseLocationCookie,
  type LocationSource,
} from "@/lib/geo";
import { parseCategoryParam } from "@/lib/categories";
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
  cityListingMetadata,
  hasFeedFilterParams,
  isIndexableCitySlug,
  isIndexableCountrySlug,
  itemListJsonLd,
  listingPath,
  withFeaturedDealDescription,
  withFilterCanonical,
} from "@/lib/seo";
import { BRAND_NAME } from "@/lib/brand";

interface PageProps {
  params: { country: string; city: string };
  searchParams: {
    currency?: string;
    radius?: string;
    sort?: string;
    category?: string;
    page?: string;
  };
}

export async function generateMetadata({
  params,
  searchParams,
}: PageProps): Promise<Metadata> {
  if (
    isPlaceholderCitySlug(params.city) ||
    !isIndexableCitySlug(params.country, params.city)
  ) {
    return { robots: { index: false, follow: false } };
  }
  const feed = await fetchDealsFeed(
    buildDealFeedParams({
      scope: "city",
      country: params.country,
      city: params.city,
      currency: currencyForCountry(params.country),
      sort: "score",
      page: 1,
    }),
  );
  let meta = withFeaturedDealDescription(
    cityListingMetadata(params.country, params.city),
    feed.ok ? feed.data : [],
  );
  if (hasFeedFilterParams(searchParams)) {
    meta = withFilterCanonical(meta);
  }
  return meta;
}

export default async function CityPage({ params, searchParams }: PageProps) {
  if (
    isPlaceholderCitySlug(params.city) &&
    isIndexableCountrySlug(params.country)
  ) {
    permanentRedirect(listingPath(params.country));
  }
  if (!isIndexableCitySlug(params.country, params.city)) notFound();
  const { country, city } = params;
  const localCurrency = currencyForCountry(country);
  const currency: CurrencyCode = isCurrencyCode(searchParams.currency)
    ? searchParams.currency.toUpperCase()
    : localCurrency;
  const radius = parseRadiusMiles(searchParams.radius);
  const sort = parseFeedSort(searchParams.sort);
  const category = parseCategoryParam(searchParams.category);
  const page = parseFeedPage(searchParams.page);
  const countryLabel = countrySearchLabel(country);
  const cityLabel = cityDisplayLabel(country, city);
  const hasCentroid = Boolean(lookupCityCoords(country, city));
  const listingHref = listingPath(country, city);

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

  const feed = await fetchDealsFeedPage(
    buildDealFeedParams({
      scope: "city",
      country,
      city,
      currency,
      sort,
      radius,
      category,
      page,
    }),
  );
  const deals = feed.ok ? areaListingDeals(feed.data.deals) : [];
  const total = feed.ok ? feed.data.total : 0;
  const empty = feedEmptyMessage("city", cityLabel);
  const preservedParams = {
    currency: searchParams.currency,
    sort: searchParams.sort,
    category: searchParams.category,
    radius: searchParams.radius,
  };

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
            }. ${total} listing${total === 1 ? "" : "s"}.`}
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

        <PublisherExplainer areaLabel={`${cityLabel}, ${countryLabel}`} />

        <JsonLd
          data={[
            breadcrumbJsonLd([
              { name: BRAND_NAME, path: "/" },
              { name: countryLabel, path: listingPath(country) },
              { name: cityLabel, path: listingHref },
            ]),
            itemListJsonLd(`Dining deals in ${cityLabel}`, deals),
          ]}
        />

        <NewsletterDealGate>
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
