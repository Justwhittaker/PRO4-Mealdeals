"use client";

import { useEffect, useState } from "react";
import { getScrapeMetrics } from "@/lib/api";

function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

interface HeaderScrapeMetricsProps {
  initialActiveDeals?: number | null;
  initialMarkets?: number | null;
}

/** Live active deals + countries from scrape inventory metrics. */
export function HeaderScrapeMetrics({
  initialActiveDeals = null,
  initialMarkets = null,
}: HeaderScrapeMetricsProps) {
  const [activeDeals, setActiveDeals] = useState<number | null>(
    initialActiveDeals,
  );
  const [markets, setMarkets] = useState<number | null>(initialMarkets);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const result = await getScrapeMetrics();
      if (cancelled || !result.ok) return;
      setActiveDeals(result.data.activeDeals);
      setMarkets(result.data.markets);
    }

    // The server header already fetched this. Don't repeat it on hydration.
    const hasInitial = initialActiveDeals != null && initialMarkets != null;
    if (!hasInitial) void load();
    const timer = window.setInterval(() => {
      void load();
    }, 300_000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [initialActiveDeals, initialMarkets]);

  const dealsLabel =
    activeDeals == null ? "…" : formatCount(activeDeals);
  const marketsLabel = markets == null ? "…" : formatCount(markets);

  return (
    <p
      className="mx-auto max-w-6xl text-center font-display text-sm font-bold leading-tight text-citrus-300 sm:text-base"
      aria-live="polite"
    >
      <span className="inline-block max-w-full px-1">
        {dealsLabel} deals · {marketsLabel} countries
      </span>
    </p>
  );
}
