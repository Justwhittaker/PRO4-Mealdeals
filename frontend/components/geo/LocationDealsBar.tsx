"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { MapPin, RotateCcw } from "lucide-react";
import { currencyForCountry } from "@/lib/currency";
import { clearLocationPreference } from "@/lib/location-preference";
import type { GeoTarget, LocationSource } from "@/lib/geo";

interface LocationDealsBarProps {
  target: GeoTarget;
  source: LocationSource | "fallback";
  /** Homepage shows nationwide deals for the geolocated country. */
  scope?: "city" | "country";
}

export function LocationDealsBar({
  target,
  source,
  scope = "city",
}: LocationDealsBarProps) {
  const router = useRouter();
  const currency = currencyForCountry(target.countryCode);
  const href =
    scope === "country"
      ? `/${target.countryCode}?currency=${currency}`
      : `/${target.countryCode}/${target.citySlug}?currency=${currency}`;
  const placeLabel =
    scope === "country" ? target.countryLabel : target.cityLabel;

  function useMyLocation() {
    clearLocationPreference();
    router.refresh();
  }

  const sourceLabel =
    source === "search"
      ? "from your search"
      : source === "geo"
        ? "near you"
        : source === "manual"
          ? "you chose"
          : "default area";

  return (
    <div className="border-b border-burgundy-200 bg-burgundy-50">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-2 px-4 py-2.5 text-center sm:justify-between sm:px-6 sm:text-left">
        <p className="flex items-start justify-center gap-2 text-sm text-charcoal-200 sm:items-center sm:justify-start">
          <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-burgundy-500 sm:mt-0" />
          <span>
            Showing deals{" "}
            {scope === "country" ? "across" : "for"}{" "}
            <Link
              href={href}
              className="font-medium text-charcoal-50 underline-offset-2 hover:underline"
            >
              {placeLabel}
            </Link>{" "}
            <span className="text-charcoal-400">({sourceLabel})</span>
            {scope === "country"
              ? ". Search a city to zoom in."
              : ". Search a city to switch areas."}
          </span>
        </p>
        {source === "search" || source === "fallback" ? (
          <button
            type="button"
            onClick={useMyLocation}
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium uppercase tracking-wider text-burgundy-600 transition hover:bg-white"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Use my location
          </button>
        ) : null}
      </div>
    </div>
  );
}
