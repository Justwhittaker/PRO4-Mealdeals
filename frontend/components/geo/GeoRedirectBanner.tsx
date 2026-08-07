"use client";

import Link from "next/link";
import { useState } from "react";
import { MapPin, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { GeoTarget } from "@/lib/geo";

export type { GeoTarget };

interface GeoRedirectBannerProps {
  target: GeoTarget | null;
  detectedCountry?: string | null;
}

/** Optional prompt to open the full city portal (homepage uses LocationDealsBar). */
export function GeoRedirectBanner({
  target,
  detectedCountry,
}: GeoRedirectBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (!target || dismissed) return null;

  const href = `/${target.countryCode}/${target.citySlug}`;

  return (
    <div className="animate-fade-in border-b border-burgundy-200 bg-burgundy-50 text-charcoal-50">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-start gap-3 sm:items-center">
          <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-burgundy-500 sm:mt-0" />
          <p className="text-sm text-charcoal-200">
            {detectedCountry ? (
              <>
                Looking like you&apos;re in{" "}
                <span className="font-medium text-charcoal-50">
                  {target.cityLabel}, {target.countryLabel}
                </span>
                . Open your local deals?
              </>
            ) : (
              <>Browse deals near you in {target.cityLabel}.</>
            )}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button asChild size="sm" className="hidden sm:inline-flex">
            <Link href={href}>Go to {target.cityLabel}</Link>
          </Button>
          <Button asChild size="sm" className="sm:hidden">
            <Link href={href}>Go local</Link>
          </Button>
          <button
            type="button"
            onClick={() => setDismissed(true)}
            className="rounded-md p-1.5 text-charcoal-400 transition hover:bg-white hover:text-charcoal-100"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
