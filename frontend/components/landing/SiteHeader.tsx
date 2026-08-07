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
      <div className="relative mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <BrandLogo size="md" priority />

        <div className="pointer-events-none absolute inset-x-0 flex justify-center px-4">
          <div className="pointer-events-auto">
            <HeaderScrapeMetrics
              initialActiveDeals={activeDeals}
              initialMarkets={markets}
            />
          </div>
        </div>

        <nav
          className="relative z-10 flex shrink-0 items-center justify-end gap-1 sm:gap-2"
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
