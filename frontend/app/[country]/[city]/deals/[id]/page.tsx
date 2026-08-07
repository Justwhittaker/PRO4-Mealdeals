import Link from "next/link";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DealHeroMedia } from "@/components/deals/DealHeroMedia";
import { LocationHeader } from "@/components/deals/LocationHeader";
import { fetchDeal, fetchValueCalculator } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import { dealBadge } from "@/lib/priority";

interface PageProps {
  params: { country: string; city: string; id: string };
}

export default async function DealDetailPage({ params }: PageProps) {
  const { country, city, id } = params;
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
  const websiteUrl = deal.cleanUrl || deal.affiliateUrl || null;
  let websiteLabel = websiteUrl;
  if (websiteUrl) {
    try {
      websiteLabel = new URL(websiteUrl).hostname.replace(/^www\./, "");
    } catch {
      websiteLabel = websiteUrl;
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      <LocationHeader
        country={country}
        city={city}
        title={deal.title}
        subtitle={deal.restaurantName}
      />

      <article className="animate-fade-up space-y-6">
        <DealHeroMedia
          imageUrl={deal.imageUrl}
          logoUrl={deal.logoUrl}
          restaurantName={deal.restaurantName}
          aspectClassName="aspect-[16/9]"
          className="rounded-2xl border border-charcoal-700"
        />

        <div className="flex flex-wrap items-center gap-3">
          {badge ? <Badge variant={badge.variant}>{badge.label}</Badge> : null}
          <span className="text-2xl font-semibold text-citrus-300">
            {formatMoney(deal.price, deal.currency)}
          </span>
          {deal.originalPrice && deal.originalPrice > deal.price ? (
            <span className="text-charcoal-500 line-through">
              {formatMoney(deal.originalPrice, deal.currency)}
            </span>
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

        {value.ok ? (
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

        <div className="flex flex-wrap gap-3 pt-2">
          <Button asChild size="lg">
            <a
              href={`/go/${deal.id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              Claim this deal
            </a>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href={`/${country}/${city}`}>
              More in {city.replace(/-/g, " ")}
            </Link>
          </Button>
        </div>
      </article>
    </main>
  );
}
