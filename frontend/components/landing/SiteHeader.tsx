import Link from "next/link";
import { AccountMenu } from "@/components/landing/AccountMenu";
import { BrandLogo } from "@/components/landing/BrandLogo";
import { HeaderScrapeMetrics } from "@/components/landing/HeaderScrapeMetrics";
import { NewsletterMenu } from "@/components/newsletter/NewsletterMenu";
import { getScrapeMetrics } from "@/lib/api";

export async function SiteHeader() {
  const metrics = await getScrapeMetrics();
  const activeDeals = metrics.ok ? metrics.data.activeDeals : null;
  const markets = metrics.ok ? metrics.data.markets : null;

  return (
    <header className="relative z-[80] border-b border-charcoal-700 bg-white">
      {/* Full-width strip — never overlapped by logo/nav */}
      <div className="border-b border-charcoal-800 bg-charcoal-950 px-3 py-1.5 sm:px-6">
        <HeaderScrapeMetrics
          initialActiveDeals={activeDeals}
          initialMarkets={markets}
        />
      </div>

      {/*
        Mobile: logo on its own row, then About / Subscribe / Login hard-right.
        sm+: single row, logo left / nav right.
      */}
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-1 px-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-3 sm:px-6">
        <div className="relative z-[90] min-w-0 self-start overflow-hidden">
          <BrandLogo size="md" priority />
        </div>

        <nav
          className="relative z-[90] flex w-full shrink-0 items-center justify-end gap-0.5 sm:w-auto sm:gap-2"
          aria-label="Site"
        >
          <Link
            href="/about"
            className="rounded-md px-1.5 py-2 text-[10px] font-medium uppercase tracking-wider text-charcoal-200 transition hover:bg-burgundy-50 hover:text-burgundy-600 sm:px-2 sm:text-xs"
          >
            About
          </Link>
          <NewsletterMenu />
          <AccountMenu />
        </nav>
      </div>
    </header>
  );
}
