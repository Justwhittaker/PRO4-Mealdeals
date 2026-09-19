import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DealHeroMedia } from "@/components/deals/DealHeroMedia";
import { LocationHeader } from "@/components/deals/LocationHeader";
import { NewsletterDealGate } from "@/components/newsletter/NewsletterDealGate";
import { fetchDeal, fetchValueCalculator } from "@/lib/api";
import { dealCtaLabel, dealLinkHint } from "@/lib/deal-link";
import { formatMoney } from "@/lib/currency";
import { cityDisplayLabel, countrySearchLabel } from "@/lib/geo";
import { dealBadge } from "@/lib/priority";
import { JsonLd } from "@/components/seo/JsonLd";
import {
  breadcrumbJsonLd,
  dealListingMetadata,
  isReservedGeoSlug,
  listingPath,
  offerJsonLd,
} from "@/lib/seo";
import { BRAND_NAME } from "@/lib/brand";

interface PageProps {
  params: { country: string; city: string; id: string };
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  if (isReservedGeoSlug(params.country) || isReservedGeoSlug(params.city)) {
    return { robots: { index: false, follow: false } };
  }
  const result = await fetchDeal(params.id, {
    country: params.country,
    city: params.city,
  });
  if (!result.ok) {
    return { robots: { index: false, follow: false } };
  }
  return dealListingMetadata(result.data, params.country, params.city);
}

export default async function DealDetailPage({ params }: PageProps) {
  const { country, city, id } = params;
  if (isReservedGeoSlug(country) || isReservedGeoSlug(city)) notFound();
  const result = await fetchDeal(id, { country, city });

  if (!result.ok) {
    if (result.status === 404) notFound();
    return (
      <main className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <LocationHeader country={country} city={city} title="Deal unavailable" />
        <Card>
          <CardContent className="space-y-3 p-6">
            <p className="text-charcoal-200">
              We couldn&apos;t load this deal from the API.
            </p>
            <p className="text-sm text-charcoal-500">{result.error}</p>
            <Button asChild variant="outline">
              <Link href={`/${country}/${city}`}>Back to city feed</Link>
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  const deal = result.data;
  const badge = dealBadge(deal);
  const value = await fetchValueCalculator(id);
  const websiteUrl =
    deal.outboundUrl || deal.cleanUrl || deal.affiliateUrl || null;
  const ctaLabel =
    deal.ctaLabel ?? dealCtaLabel(deal.linkKind, deal.restaurantName);
  const linkHint = dealLinkHint(deal.linkKind);
  let websiteLabel = websiteUrl;
  if (websiteUrl) {
    try {
      websiteLabel = new URL(websiteUrl).hostname.replace(/^www\./, "");
    } catch {
      websiteLabel = websiteUrl;
    }
  }

  const cityLabel = cityDisplayLabel(country, city);
  const countryLabel = countrySearchLabel(country);

  return (
    <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      <JsonLd
        data={[
          breadcrumbJsonLd([
            { name: BRAND_NAME, path: "/" },
            { name: countryLabel, path: listingPath(country) },
            { name: cityLabel, path: listingPath(country, city) },
            { name: deal.title, path: listingPath(country, city, deal.id) },
          ]),
          offerJsonLd(deal, country, city),
        ]}
      />
      <NewsletterDealGate compact>
        <LocationHeader
          country={country}
          city={city}
          title={deal.title}
          subtitle={
            deal.areaLabel
              ? `${deal.areaLabel} · ${deal.restaurantName}`
              : deal.restaurantName
          }
        />

        <article className="animate-fade-up mt-6 space-y-6">
          <DealHeroMedia
            imageUrl={deal.imageUrl}
            logoUrl={deal.logoUrl}
            restaurantName={deal.restaurantName}
            imageAlt={`${deal.title} — ${deal.restaurantName} in ${cityLabel}`}
            aspectClassName="aspect-[16/9]"
            className="rounded-2xl border border-charcoal-700"
          />

          <div className="flex flex-wrap items-center gap-3">
            {badge ? <Badge variant={badge.variant}>{badge.label}</Badge> : null}
            {deal.price > 0 ? (
              <>
                <span className="text-2xl font-semibold text-citrus-300">
                  {formatMoney(deal.price, deal.currency)}
                </span>
                {deal.originalPrice && deal.originalPrice > deal.price ? (
                  <span className="text-charcoal-500 line-through">
                    {formatMoney(deal.originalPrice, deal.currency)}
                  </span>
                ) : null}
              </>
            ) : null}
          </div>

          {deal.description ? (
            <p className="text-lg leading-relaxed text-charcoal-200">
              {deal.description}
            </p>
          ) : null}

          {websiteUrl ? (
            <p className="text-sm text-charcoal-300">
              Website:{" "}
              <a
                href={websiteUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-burgundy-600 underline-offset-2 hover:underline break-all"
              >
                {websiteLabel}
              </a>
            </p>
          ) : null}

          {deal.aboutBlurb ? (
            <p className="max-w-2xl text-sm leading-relaxed text-charcoal-200">
              {deal.aboutBlurb}
            </p>
          ) : null}

          {deal.price > 0 && value.ok ? (
            <Card>
              <CardContent className="grid gap-3 p-5 sm:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-wider text-charcoal-500">
                    Market value
                  </p>
                  <p className="mt-1 text-lg text-charcoal-50">
                    {formatMoney(value.data.marketValue, value.data.currency)}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-charcoal-500">
                    You save
                  </p>
                  <p className="mt-1 text-lg text-citrus-300">
                    {formatMoney(value.data.savings, value.data.currency)}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-charcoal-500">
                    Value score
                  </p>
                  <p className="mt-1 text-lg text-charcoal-50">
                    {value.data.savingsPercent}% off
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : null}

          <div className="space-y-2 pt-2">
            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg">
                <a
                  href={`/go/${deal.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {ctaLabel}
                </a>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href={`/${country}/${city}`}>
                  More in {cityDisplayLabel(country, city)}
                </Link>
              </Button>
            </div>
            {linkHint ? (
              <p className="text-sm text-charcoal-400">{linkHint}</p>
            ) : null}
          </div>
        </article>
      </NewsletterDealGate>
    </main>
  );
}
