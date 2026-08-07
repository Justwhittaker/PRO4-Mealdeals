import type { ReactNode } from "react";
import Link from "next/link";

interface LocationHeaderProps {
  country: string;
  city?: string;
  title?: string;
  subtitle?: ReactNode;
}

function titleCase(slug: string) {
  return slug
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

const COUNTRY_LABELS: Record<string, string> = {
  uk: "United Kingdom",
  gb: "United Kingdom",
  us: "United States",
  ie: "Ireland",
  au: "Australia",
  ca: "Canada",
  nz: "New Zealand",
  za: "South Africa",
};

export function LocationHeader({
  country,
  city,
  title,
  subtitle,
}: LocationHeaderProps) {
  const countryLabel = COUNTRY_LABELS[country.toLowerCase()] ?? titleCase(country);
  const cityLabel = city ? titleCase(city) : null;

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
