"use client";

import { useEffect, useState } from "react";
import { LocationDealsBar } from "@/components/geo/LocationDealsBar";
import {
  LOCATION_COOKIE,
  LOCATION_SOURCE_COOKIE,
  normalizeCountrySlug,
  parseLocationCookie,
  type GeoTarget,
  type LocationSource,
} from "@/lib/geo";

interface CityLocationBannerProps {
  country: string;
  city: string;
  countryLabel: string;
  cityLabel: string;
}

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const prefix = `${name}=`;
  const parts = document.cookie.split("; ");
  for (const part of parts) {
    if (part.startsWith(prefix)) {
      return decodeURIComponent(part.slice(prefix.length));
    }
  }
  return undefined;
}

function pageTarget(
  country: string,
  city: string,
  countryLabel: string,
  cityLabel: string,
): GeoTarget {
  return {
    countryCode: normalizeCountrySlug(country),
    countryLabel,
    citySlug: city,
    cityLabel,
  };
}

/**
 * Location bar for a city listing. Cookie reads stay in the browser so the
 * server page does not call `cookies()` and can be cached.
 */
export function CityLocationBanner({
  country,
  city,
  countryLabel,
  cityLabel,
}: CityLocationBannerProps) {
  const [target, setTarget] = useState<GeoTarget>(() =>
    pageTarget(country, city, countryLabel, cityLabel),
  );
  const [source, setSource] = useState<LocationSource | "fallback">("geo");

  useEffect(() => {
    const pref = parseLocationCookie(readCookie(LOCATION_COOKIE));
    const raw = readCookie(LOCATION_SOURCE_COOKIE);
    const nextSource: LocationSource | "fallback" =
      raw === "search" || raw === "geo" || raw === "manual" ? raw : "geo";
    setSource(nextSource);
    if (pref && pref.citySlug === city) {
      setTarget(pref);
      return;
    }
    setTarget(pageTarget(country, city, countryLabel, cityLabel));
  }, [country, city, countryLabel, cityLabel]);

  return <LocationDealsBar target={target} source={source} scope="city" />;
}
