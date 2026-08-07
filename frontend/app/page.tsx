import { Suspense } from "react";
import { cookies, headers } from "next/headers";
import { AdvertCarousel } from "@/components/landing/AdvertCarousel";
import { LandingSearch } from "@/components/landing/LandingSearch";
import { RestaurantSearch } from "@/components/landing/RestaurantSearch";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { GeoBootstrap } from "@/components/geo/GeoBootstrap";
import { LocationDealsBar } from "@/components/geo/LocationDealsBar";
import { NewsletterPopup } from "@/components/newsletter/NewsletterPopup";
import { AreaDealGrid } from "@/components/deals/AreaDealGrid";
import { RadiusSelector } from "@/components/deals/RadiusSelector";
import { fetchDealsFeed } from "@/lib/api";
import { currencyForCountry } from "@/lib/currency";
import {
  LOCATION_COOKIE,
  LOCATION_SOURCE_COOKIE,
  countrySearchLabel,
  defaultGeoTarget,
  parseLocationCookie,
  resolveGeoFromHeaders,
  type LocationSource,
} from "@/lib/geo";
import {
  filterDealsByCategory,
  parseCategoryParam,
} from "@/lib/categories";
import { buildDealFeedParams } from "@/lib/deal-feed-query";
import { areaListingDeals } from "@/lib/priority";
import { parseFeedSort, parseRadiusMiles } from "@/lib/radius";

function resolveHomeLocation(): {
  target: ReturnType<typeof defaultGeoTarget>;
  source: LocationSource | "fallback";
  needsClientGeo: boolean;
} {
  const jar = cookies();
  const pref = parseLocationCookie(jar.get(LOCATION_COOKIE)?.value);
  const source = jar.get(LOCATION_SOURCE_COOKIE)?.value as
    | LocationSource
    | undefined;
  const geo = resolveGeoFromHeaders(headers());

  if (pref && source === "search") {
    return { target: pref, source: "search", needsClientGeo: false };
  }

  if (geo) {
    return { target: geo, source: "geo", needsClientGeo: false };
  }

  if (pref && source === "geo") {
    return { target: pref, source: "geo", needsClientGeo: false };
  }

  return {
    target: pref ?? defaultGeoTarget(),
    source: pref ? (source ?? "geo") : "fallback",
    needsClientGeo: true,
  };
}

export default async function HomePage({
  searchParams,
}: {
  searchParams?: { radius?: string; sort?: string; category?: string };
}) {
  const { target, source, needsClientGeo } = resolveHomeLocation();
  const feedCountry = target.countryCode;
  const countryLabel = countrySearchLabel(feedCountry);
  const hubLabel = target.cityLabel;
  const currency = currencyForCountry(feedCountry);
  const radius = parseRadiusMiles(searchParams?.radius);
  const sort = parseFeedSort(searchParams?.sort);
  const category = parseCategoryParam(searchParams?.category);

  // Country-wide feed for the geolocated country — all cities, all categories.
  const feed = await fetchDealsFeed(
    buildDealFeedParams({
      scope: "country",
      country: feedCountry,
      currency,
      sort,
    }),
  );
  const deals = feed.ok ? feed.data : [];
  const listed = filterDealsByCategory(areaListingDeals(deals), category);
  const carouselDeals = listed.slice(0, 12);
  const restaurants = listed.slice(0, 8).map((d) => ({
    label: `${d.restaurantName}, ${d.city.replace(/-/g, " ")}`,
    href: `/${d.country}/${d.city}`,
  }));

  return (
    <div className="relative min-h-screen bg-white">
      <LocationDealsBar target={target} source={source} scope="country" />
      <GeoBootstrap enabled={needsClientGeo} />
      <NewsletterPopup />

      <main>
        <p className="animate-fade-up bg-white px-4 py-3 text-center font-display text-xl text-charcoal-50 sm:px-6 sm:text-2xl">
          HOT DEALS across {countryLabel} — all categories
          {hubLabel ? ` (near ${hubLabel})` : ""}.
        </p>
        <section className="hero-atmosphere grain relative border-b border-charcoal-700">
          <div className="relative z-10 mx-auto max-w-6xl px-4 py-4 sm:px-6 sm:py-5">
            <div className="animate-fade-up opacity-0 [animation-delay:120ms] [animation-fill-mode:forwards]">
              <LandingSearch category={category} />
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[90rem] px-4 py-5 sm:px-6 sm:py-6">
          <div className="mb-3 flex flex-col items-center gap-1 text-center">
            <div>
              <h2 className="font-display text-2xl text-charcoal-50 sm:text-3xl">
                Today&apos;s adverts across {countryLabel}
              </h2>
              <p className="mt-1 text-sm text-charcoal-400">
                HOT Deals for {countryLabel} — every listing in every category
                ({listed.length} shown).
              </p>
            </div>
          </div>
          <AdvertCarousel deals={carouselDeals} />
          <div className="mx-auto mt-6 flex w-full max-w-4xl flex-col items-center justify-center gap-3 px-1 sm:flex-row">
            <RestaurantSearch
              restaurants={restaurants}
              className="w-full min-w-0 max-w-md"
            />
            <Suspense fallback={null}>
              <div className="shrink-0">
                <RadiusSelector
                  radius={radius}
                  sort={sort}
                  category={category}
                  showRadius={false}
                  showCategory={false}
                />
              </div>
            </Suspense>
          </div>
          {!feed.ok ? (
            <p className="mt-6 text-center text-sm text-charcoal-400">
              Feed unavailable ({feed.error}). Start the API to load live
              adverts.
            </p>
          ) : null}

          <div className="mt-12 border-t border-charcoal-700 pt-10">
            <AreaDealGrid
              deals={listed}
              cityLabel={countryLabel}
              category={category}
              emptyMessage={`No deals listed across ${countryLabel} yet.`}
              emptyHint="Search another country or check back soon."
            />
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
