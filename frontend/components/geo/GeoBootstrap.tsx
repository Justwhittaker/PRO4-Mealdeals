"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { nearestCity, cityToTarget, type GeoTarget } from "@/lib/geo";
import { setLocationPreference } from "@/lib/location-preference";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface GeoBootstrapProps {
  /** When true, ask the browser / GPS and persist nearest Dine A Deal city. */
  enabled: boolean;
}

async function resolveFromApi(lat: number, lon: number): Promise<GeoTarget | null> {
  try {
    const qs = new URLSearchParams({ lat: String(lat), lon: String(lon) });
    const res = await fetch(
      `${API_URL.replace(/\/$/, "")}/api/v1/geo/resolve?${qs}`,
      { cache: "no-store" },
    );
    if (!res.ok) return null;
    const data = (await res.json()) as {
      country_slug: string;
      city_slug: string;
      city: string;
    };
    return {
      countryCode: data.country_slug,
      countryLabel: data.country_slug.toUpperCase(),
      citySlug: data.city_slug,
      cityLabel: data.city,
    };
  } catch {
    return null;
  }
}

/**
 * Client-side geolocation when edge IP headers are missing (local/dev)
 * or the visitor has not searched a location yet.
 */
export function GeoBootstrap({ enabled }: GeoBootstrapProps) {
  const router = useRouter();
  const ran = useRef(false);
  const [status, setStatus] = useState<"idle" | "detecting" | "done" | "denied">(
    "idle",
  );

  useEffect(() => {
    if (!enabled || ran.current) return;
    if (typeof navigator === "undefined" || !navigator.geolocation) return;
    ran.current = true;
    setStatus("detecting");

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        const fromApi = await resolveFromApi(latitude, longitude);
        const target =
          fromApi ?? cityToTarget(nearestCity(latitude, longitude));
        setLocationPreference(target, "geo");
        setStatus("done");
        router.refresh();
      },
      () => {
        setStatus("denied");
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 600_000 },
    );
  }, [enabled, router]);

  if (!enabled || status === "idle" || status === "done") return null;

  if (status === "denied") {
    return (
      <p className="mx-auto max-w-6xl px-4 py-2 text-center text-xs text-charcoal-400 sm:px-6">
        Location access blocked — search a city to load local deals, or allow
        location and refresh.
      </p>
    );
  }

  return (
    <p className="mx-auto max-w-6xl px-4 py-2 text-center text-xs text-charcoal-400 sm:px-6">
      Detecting your area for local deals…
    </p>
  );
}
