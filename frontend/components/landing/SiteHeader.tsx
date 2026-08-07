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
    <header className="border-b border-charcoal-700 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-3 sm:px-6">
        <div className="flex items-center justify-between gap-3">
          <BrandLogo size="md" priority />

          <nav
            className="flex shrink-0 items-center justify-end gap-1 sm:gap-2"
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

        <div className="flex items-center justify-center gap-6 sm:gap-10">
          <p className="text-center font-display text-sm font-bold leading-tight text-charcoal-200 sm:text-base">
            <span className="block">Hottest Deals</span>
            <span className="block">Daily</span>
          </p>
          <HeaderScrapeMetrics
            initialActiveDeals={activeDeals}
            initialMarkets={markets}
          />
        </div>
      </div>
    </header>
  );
}
