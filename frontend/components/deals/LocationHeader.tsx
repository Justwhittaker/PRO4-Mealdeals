import type { ReactNode } from "react";
import Link from "next/link";
import { cityDisplayLabel, countrySearchLabel } from "@/lib/geo";

interface LocationHeaderProps {
  country: string;
  city?: string;
  title?: string;
  subtitle?: ReactNode;
}

export function LocationHeader({
  country,
  city,
  title,
  subtitle,
}: LocationHeaderProps) {
  const countryLabel = countrySearchLabel(country);
  const cityLabel = city ? cityDisplayLabel(country, city) : null;

  return (
    <header className="mb-8 animate-fade-up">
      <nav className="mb-3 flex flex-wrap items-center gap-2 text-sm text-charcoal-400">
        <Link href="/" className="hover:text-citrus-400 transition-colors">
          Dine A Deal
        </Link>
        <span aria-hidden>/</span>
        <Link
          href={`/${country}`}
          className="hover:text-citrus-400 transition-colors"
        >
          {countryLabel}
        </Link>
        {cityLabel ? (
          <>
            <span aria-hidden>/</span>
            <span className="text-charcoal-200">{cityLabel}</span>
          </>
        ) : null}
      </nav>
      <h1 className="font-display text-3xl font-semibold tracking-tight text-charcoal-50 sm:text-4xl">
        {title ??
          (cityLabel
            ? `Deals in ${cityLabel}`
            : `Deals across ${countryLabel}`)}
      </h1>
      {subtitle ? (
        <p className="mt-2 max-w-2xl text-charcoal-300">{subtitle}</p>
      ) : null}
    </header>
  );
}
