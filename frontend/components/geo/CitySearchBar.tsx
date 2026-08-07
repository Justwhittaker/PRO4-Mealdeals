"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { scrapeAreaDeals } from "@/lib/api";
import { currencyForCountry } from "@/lib/currency";
import {
  countrySearchLabel,
  listCountries,
  resolveLocationQuery,
  type CityOption,
  type CountryOption,
} from "@/lib/geo";
import { setLocationPreference } from "@/lib/location-preference";

/** Country → nested city search for city/country deal pages. */
export function CitySearchBar() {
  const router = useRouter();
  const countries = useMemo(() => listCountries(), []);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeCountry, setActiveCountry] = useState<CountryOption | null>(
    null,
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const q = query.trim().toLowerCase();

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

  const nestedCities = useMemo(() => {
    if (!activeCountry) return [] as CityOption[];
    if (!q) return activeCountry.cities;
    return activeCountry.cities.filter(
      (city) =>
        city.label.toLowerCase().includes(q) ||
        city.city.toLowerCase().includes(q),
    );
  }, [activeCountry, q]);

  async function goCity(city: CityOption) {
    setError(null);
    setPending(true);
    setOpen(false);
    setLocationPreference(
      {
        countryCode: city.country,
        countryLabel: countrySearchLabel(city.country),
        citySlug: city.city,
        cityLabel: city.label,
      },
      "search",
    );
    void scrapeAreaDeals(city.country, city.city);
    const currency = currencyForCountry(city.country);
    router.push(`/${city.country}/${city.city}?currency=${currency}`);
    setPending(false);
  }

  function goCountry(country: CountryOption) {
    setOpen(false);
    setPending(true);
    setError(null);
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
    setQuery("");
    setOpen(true);
    setError(null);
  }

  function backToCountries() {
    setActiveCountry(null);
    setQuery("");
    setOpen(true);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const raw = query.trim();
    if (!raw && !activeCountry) {
      setError("Pick a country for all deals, or browse cities.");
      return;
    }

    if (activeCountry) {
      if (nestedCities[0]) {
        await goCity(nestedCities[0]);
        return;
      }
      setError("No cities match that search.");
      return;
    }

    const resolved = resolveLocationQuery(raw);
    if (resolved) {
      setPending(true);
      setLocationPreference(resolved, "search");
      void scrapeAreaDeals(resolved.countryCode, resolved.citySlug);
      const currency = currencyForCountry(resolved.countryCode);
      router.push(
        `/${resolved.countryCode}/${resolved.citySlug}?currency=${currency}`,
      );
      setPending(false);
      return;
    }

    const countryHit = filteredCountries[0];
    if (countryHit) {
      goCountry(countryHit);
      return;
    }

    setError("Try a country like United Kingdom or United States.");
  }

  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-2 sm:flex-row sm:items-start"
    >
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-burgundy-500" />
        <Input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            setError(null);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 180)}
          placeholder={
            activeCountry
              ? `Search cities in ${activeCountry.label}`
              : "Search country — e.g. United Kingdom"
          }
          className="h-11 pl-10"
          aria-label="Search country then city"
        />
        {open ? (
          <ul className="absolute left-0 right-0 top-full z-[100] mt-1 max-h-64 w-full overflow-auto rounded-md border border-charcoal-700 bg-white py-1 shadow-deal">
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
                {nestedCities.map((city) => (
                  <li key={`${city.country}-${city.city}`}>
                    <button
                      type="button"
                      className="w-full px-3 py-2 text-left text-sm text-charcoal-100 hover:bg-burgundy-50 hover:text-burgundy-700"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => void goCity(city)}
                    >
                      {city.label}
                    </button>
                  </li>
                ))}
              </>
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
      <Button type="submit" disabled={pending} className="sm:w-auto">
        {pending ? "Switching…" : "Show deals"}
      </Button>
      {error ? (
        <p className="text-xs text-burgundy-600 sm:basis-full" role="alert">
          {error}
        </p>
      ) : null}
    </form>
  );
}
