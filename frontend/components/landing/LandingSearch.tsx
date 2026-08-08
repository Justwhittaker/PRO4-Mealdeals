"use client";

import { Suspense, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Mic, Search } from "lucide-react";
import { CategorySelector } from "@/components/deals/CategorySelector";
import { Input } from "@/components/ui/input";
import { scrapeAreaDeals } from "@/lib/api";
import type { ParentCategoryId } from "@/lib/categories";
import { currencyForCountry } from "@/lib/currency";
import {
  countrySearchLabel,
  listCountries,
  resolveLocationQuery,
  type CityOption,
  type CountryOption,
  type GeoTarget,
} from "@/lib/geo";
import { setLocationPreference } from "@/lib/location-preference";

interface LandingSearchProps {
  category?: ParentCategoryId | "all";
}

async function goToArea(target: GeoTarget, router: ReturnType<typeof useRouter>) {
  setLocationPreference(target, "search");
  void scrapeAreaDeals(target.countryCode, target.citySlug);
  const currency = currencyForCountry(target.countryCode);
  router.push(
    `/${target.countryCode}/${target.citySlug}?currency=${currency}`,
  );
}

export function LandingSearch({ category = "all" }: LandingSearchProps) {
  const router = useRouter();
  const countries = useMemo(() => listCountries(), []);
  const [locationQuery, setLocationQuery] = useState("");
  const [openLocation, setOpenLocation] = useState(false);
  const [activeCountry, setActiveCountry] = useState<CountryOption | null>(
    null,
  );
  const [pending, setPending] = useState(false);

  const q = locationQuery.trim().toLowerCase();

  const filteredCountries = countries.filter((c) => {
    if (!q || activeCountry) return true;
    return (
      c.label.toLowerCase().includes(q) ||
      c.code.toLowerCase().includes(q) ||
      c.cities.some(
        (city) =>
          city.label.toLowerCase().includes(q) ||
          city.city.toLowerCase().includes(q),
      )
    );
  });

  const nestedCities: CityOption[] = useMemo(() => {
    if (!activeCountry) return [];
    if (!q) return activeCountry.cities;
    return activeCountry.cities.filter(
      (city) =>
        city.label.toLowerCase().includes(q) ||
        city.city.toLowerCase().includes(q),
    );
  }, [activeCountry, q]);

  async function goCity(city: CityOption) {
    setOpenLocation(false);
    setPending(true);
    await goToArea(
      {
        countryCode: city.country,
        countryLabel: countrySearchLabel(city.country),
        citySlug: city.city,
        cityLabel: city.label,
      },
      router,
    );
    setPending(false);
  }

  function goCountry(country: CountryOption) {
    setOpenLocation(false);
    setPending(true);
    const currency = currencyForCountry(country.code);
    const hub = country.cities[0];
    if (hub) {
      setLocationPreference(
        {
          countryCode: hub.country,
          countryLabel: country.label,
          citySlug: hub.city,
          cityLabel: hub.label,
        },
        "search",
      );
    }
    router.push(`/${country.code}?currency=${currency}`);
    setPending(false);
  }

  function browseCities(country: CountryOption) {
    setActiveCountry(country);
    setLocationQuery("");
    setOpenLocation(true);
  }

  function backToCountries() {
    setActiveCountry(null);
    setLocationQuery("");
    setOpenLocation(true);
  }

  async function submitLocationQuery() {
    const raw = locationQuery.trim();
    if (!raw) return;

    if (activeCountry) {
      if (nestedCities[0]) {
        await goCity(nestedCities[0]);
      }
      return;
    }

    const resolved = resolveLocationQuery(raw);
    if (resolved) {
      setPending(true);
      setOpenLocation(false);
      await goToArea(resolved, router);
      setPending(false);
      return;
    }

    const countryHit = filteredCountries[0];
    if (countryHit) {
      goCountry(countryHit);
    }
  }

  return (
    <div className="relative z-10 mx-auto grid w-full max-w-4xl gap-3 sm:grid-cols-2">
      <div className={`relative ${openLocation ? "z-20" : ""}`}>
        <label htmlFor="search-country" className="sr-only">
          Search country
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-burgundy-500" />
          <Input
            id="search-country"
            value={locationQuery}
            onChange={(e) => {
              setLocationQuery(e.target.value);
              setOpenLocation(true);
            }}
            onFocus={() => setOpenLocation(true)}
            onBlur={() => setTimeout(() => setOpenLocation(false), 180)}
            onKeyDown={(e) => {
              if (e.key === "Escape" && activeCountry) {
                e.preventDefault();
                backToCountries();
                return;
              }
              if (e.key === "Enter") {
                e.preventDefault();
                void submitLocationQuery();
              }
            }}
            placeholder={
              pending
                ? "Loading area…"
                : activeCountry
                  ? `Search cities in ${activeCountry.label}`
                  : "Search country (e.g. United Kingdom)"
            }
            className="h-12 border-charcoal-600 bg-white pl-10 pr-10 text-base shadow-sm"
            autoComplete="off"
            disabled={pending}
          />
          <Mic
            className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-charcoal-400"
            aria-hidden
          />
        </div>
        {openLocation ? (
          <ul className="absolute left-0 right-0 top-full z-[100] mt-1 max-h-80 w-full overflow-auto rounded-md border border-charcoal-700 bg-white py-1 shadow-deal">
            {activeCountry ? (
              <>
                <li>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-burgundy-600 hover:bg-burgundy-50"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={backToCountries}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    All countries
                  </button>
                </li>
                <li className="px-3 py-1 text-[10px] uppercase tracking-wider text-charcoal-400">
                  Cities in {activeCountry.label}
                </li>
                {nestedCities.length === 0 ? (
                  <li className="px-3 py-2 text-sm text-charcoal-400">
                    No cities match that search.
                  </li>
                ) : (
                  nestedCities.map((city) => (
                    <li key={`${city.country}-${city.city}`}>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm text-charcoal-100 hover:bg-burgundy-50 hover:text-burgundy-700"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => void goCity(city)}
                      >
                        <span>{city.label}</span>
                        <span className="text-xs uppercase tracking-wider text-charcoal-400">
                          {city.country}
                        </span>
                      </button>
                    </li>
                  ))
                )}
              </>
            ) : filteredCountries.length === 0 ? (
              <li className="px-3 py-2 text-sm text-charcoal-400">
                No countries match that search.
              </li>
            ) : (
              filteredCountries.map((country) => (
                <li
                  key={country.code}
                  className="flex items-stretch hover:bg-burgundy-50"
                >
                  <button
                    type="button"
                    className="min-w-0 flex-1 px-3 py-2 text-left text-sm text-charcoal-100 hover:text-burgundy-700"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => goCountry(country)}
                  >
                    {country.label}
                    <span className="mt-0.5 block text-[10px] uppercase tracking-wider text-charcoal-400">
                      All country deals
                    </span>
                  </button>
                  <button
                    type="button"
                    className="shrink-0 px-3 py-2 text-xs text-charcoal-400 hover:text-burgundy-600"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => browseCities(country)}
                    aria-label={`Browse cities in ${country.label}`}
                  >
                    {country.cities.length} cit
                    {country.cities.length === 1 ? "y" : "ies"} ›
                  </button>
                </li>
              ))
            )}
          </ul>
        ) : null}
      </div>

      <Suspense fallback={<div className="h-12 rounded-md border border-charcoal-600 bg-white" />}>
        <CategorySelector category={category} variant="hero" />
      </Suspense>
    </div>
  );
}
