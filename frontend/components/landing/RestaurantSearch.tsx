"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Mic, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { scrapeAreaDeals } from "@/lib/api";
import { currencyForCountry } from "@/lib/currency";
import {
  cityDisplayLabel,
  countrySearchLabel,
  type GeoTarget,
} from "@/lib/geo";
import { setLocationPreference } from "@/lib/location-preference";

export interface RestaurantSuggestion {
  label: string;
  href: string;
}

const FALLBACK_RESTAURANTS: RestaurantSuggestion[] = [
  { label: "Loom, Galway", href: "/ie/galway" },
  { label: "The Stag's Head, Dublin", href: "/ie/dublin" },
  { label: "Eight Restaurant, Cape Town", href: "/za/cape-town" },
];

async function goToArea(
  target: GeoTarget,
  router: ReturnType<typeof useRouter>,
) {
  setLocationPreference(target, "search");
  void scrapeAreaDeals(target.countryCode, target.citySlug);
  const currency = currencyForCountry(target.countryCode);
  router.push(
    `/${target.countryCode}/${target.citySlug}?currency=${currency}`,
  );
}

interface RestaurantSearchProps {
  restaurants?: RestaurantSuggestion[];
  className?: string;
}

export function RestaurantSearch({
  restaurants = [],
  className = "",
}: RestaurantSearchProps) {
  const router = useRouter();
  const [restaurantQuery, setRestaurantQuery] = useState("");
  const [openRestaurant, setOpenRestaurant] = useState(false);

  const restaurantOptions = useMemo(() => {
    const merged = [...restaurants, ...FALLBACK_RESTAURANTS];
    const seen = new Set<string>();
    return merged.filter((r) => {
      const key = r.label.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [restaurants]);

  const filteredRestaurants = restaurantOptions.filter((r) =>
    r.label.toLowerCase().includes(restaurantQuery.trim().toLowerCase()),
  );

  function goRestaurant(href: string) {
    setOpenRestaurant(false);
    const parts = href.split("/").filter(Boolean);
    if (parts.length >= 2) {
      const country = parts[0]!;
      const city = parts[1]!;
      void goToArea(
        {
          countryCode: country,
          countryLabel: countrySearchLabel(country),
          citySlug: city,
          cityLabel: cityDisplayLabel(country, city),
        },
        router,
      );
      return;
    }
    router.push(href);
  }

  return (
    <div className={`relative w-full ${className}`}>
      <label htmlFor="search-restaurants" className="sr-only">
        Search restaurants
      </label>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-burgundy-500" />
        <Input
          id="search-restaurants"
          value={restaurantQuery}
          onChange={(e) => {
            setRestaurantQuery(e.target.value);
            setOpenRestaurant(true);
          }}
          onFocus={() => setOpenRestaurant(true)}
          onBlur={() => setTimeout(() => setOpenRestaurant(false), 150)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && filteredRestaurants[0]) {
              e.preventDefault();
              goRestaurant(filteredRestaurants[0].href);
            }
          }}
          placeholder="Search restaurants"
          className="h-12 border-charcoal-600 bg-white pl-10 pr-10 text-base shadow-sm"
          autoComplete="off"
        />
        <Mic
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-charcoal-400"
          aria-hidden
        />
      </div>
      {openRestaurant && filteredRestaurants.length > 0 ? (
        <ul className="absolute left-0 right-0 top-full z-[100] mt-1 max-h-56 w-full overflow-auto rounded-md border border-charcoal-700 bg-white py-1 shadow-deal">
          {filteredRestaurants.slice(0, 8).map((r) => (
            <li key={r.label}>
              <button
                type="button"
                className="w-full px-3 py-2 text-left text-sm text-charcoal-100 hover:bg-burgundy-50 hover:text-burgundy-700"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => goRestaurant(r.href)}
              >
                {r.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
