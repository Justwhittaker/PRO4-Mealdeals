"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { DealGoCta } from "@/components/deals/DealGoCta";
import { Button } from "@/components/ui/button";
import { cityDisplayLabel } from "@/lib/geo";
import { utmQueryString } from "@/lib/newsletter-storage";

interface DealOutboundActionsProps {
  dealId: string;
  country: string;
  city: string;
  ctaLabel: string;
  linkHint: string | null;
  websiteUrl: string | null;
  websiteLabel: string | null;
  /** Website line sits above the about blurb; the button row stays at the bottom. */
  part: "website" | "actions";
}

function referralFromSearch(search: string): string {
  return utmQueryString(search);
}

export function DealOutboundActionsView({
  dealId,
  country,
  city,
  ctaLabel,
  linkHint,
  websiteUrl,
  websiteLabel,
  referralSearch,
  part,
}: DealOutboundActionsProps & { referralSearch: string }) {
  if (part === "website") {
    if (!websiteUrl) return null;
    return (
      <p className="text-sm text-charcoal-300">
        Website:{" "}
        <DealGoCta
          dealId={dealId}
          label={websiteLabel ?? "Venue website"}
          variant="link"
          referralSearch={referralSearch}
        />
      </p>
    );
  }
  if (part !== "actions") {
    const unexpected: never = part;
    return unexpected;
  }
  return (
    <div className="space-y-2 pt-2">
      <div className="flex flex-wrap gap-3">
        <DealGoCta
          dealId={dealId}
          label={ctaLabel}
          referralSearch={referralSearch}
        />
        <Button asChild size="lg" variant="outline">
          <Link href={`/${country}/${city}`}>
            More in {cityDisplayLabel(country, city)}
          </Link>
        </Button>
      </div>
      {linkHint ? <p className="text-sm text-charcoal-400">{linkHint}</p> : null}
    </div>
  );
}

/** UTM forwarding reads the query string on the client so the deal page can stay cached. */
export function DealOutboundActions(props: DealOutboundActionsProps) {
  const searchParams = useSearchParams();
  return (
    <DealOutboundActionsView
      {...props}
      referralSearch={referralFromSearch(searchParams.toString())}
    />
  );
}

export function DealOutboundActionsFallback(props: DealOutboundActionsProps) {
  return <DealOutboundActionsView {...props} referralSearch="" />;
}
