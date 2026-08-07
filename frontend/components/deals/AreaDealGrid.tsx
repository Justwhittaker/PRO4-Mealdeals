import { DealCard, type DealCardProps } from "@/components/deals/DealCard";
import {
  groupDealsByCategory,
  type ParentCategoryId,
} from "@/lib/categories";
import { isFeaturedDeal, spreadDealsByBusiness } from "@/lib/priority";

interface AreaDealGridProps {
  deals: DealCardProps[];
  emptyMessage?: string;
  emptyHint?: string;
  cityLabel?: string;
  /** When set, subtitle includes the live radius (updates with RadiusSelector). */
  radiusMiles?: number;
  /**
   * When "all", featured first, then parent category sections in a random order
   * (meals / wine / hotels / …) so the page showcases variety. A specific
   * category filter keeps a single flat section.
   */
  category?: ParentCategoryId | "all";
}

function shuffleSections<T>(items: T[]): T[] {
  const next = [...items];
  for (let i = next.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = next[i]!;
    next[i] = next[j]!;
    next[j] = tmp;
  }
  return next;
}

/**
 * Responsive deal boxes under the carousel.
 * Mobile: 1 per row · sm: 2 · md: 3 · lg: 4 · xl: 5 · 2xl: 6
 * Caller should pass deals already featured-first + shuffled + category-filtered.
 */
export function AreaDealGrid({
  deals,
  emptyMessage = "No deals in this area right now.",
  emptyHint = "Widen the radius or search another city.",
  cityLabel,
  radiusMiles,
  category = "all",
}: AreaDealGridProps) {
  const listed = deals;

  if (listed.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-charcoal-600 bg-white px-6 py-14 text-center shadow-sm">
        <p className="font-display text-xl text-charcoal-200">{emptyMessage}</p>
        <p className="mt-2 text-sm text-charcoal-400">{emptyHint}</p>
      </div>
    );
  }

  const subtitle =
    cityLabel && radiusMiles != null
      ? `HOT Deals for ${cityLabel} — within ${radiusMiles} miles.`
      : cityLabel
        ? `HOT Deals for ${cityLabel}.`
        : null;

  const sections: {
    id: string;
    label: string | null;
    deals: DealCardProps[];
  }[] =
    category === "all"
      ? (() => {
          const featured = listed.filter(isFeaturedDeal);
          const rest = listed.filter((d) => !isFeaturedDeal(d));
          // Spread businesses within each category, then randomise category
          // section order (only when All categories is selected).
          const categorySections = shuffleSections(
            groupDealsByCategory(rest).map((section) => ({
              ...section,
              deals: spreadDealsByBusiness(section.deals),
            })),
          );
          return [
            ...(featured.length > 0
              ? [{ id: "featured", label: "Featured", deals: featured }]
              : []),
            ...categorySections,
          ];
        })()
      : [
          {
            id: category,
            label: null,
            deals: (() => {
              const featured = listed.filter(isFeaturedDeal);
              const rest = spreadDealsByBusiness(
                listed.filter((d) => !isFeaturedDeal(d)),
              );
              return featured.length > 0 ? [...featured, ...rest] : rest;
            })(),
          },
        ];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="font-display text-xl text-charcoal-50 sm:text-2xl">
            All deals{cityLabel ? ` near ${cityLabel}` : ""}
          </h3>
          {subtitle ? (
            <p className="mt-1 text-sm text-charcoal-400">{subtitle}</p>
          ) : null}
        </div>
        <p className="text-xs uppercase tracking-wider text-charcoal-400">
          {listed.length} listing{listed.length === 1 ? "" : "s"}
        </p>
      </div>

      {sections.map((section) => (
        <div key={section.id} className="space-y-4">
          {section.label ? (
            <h4 className="font-display text-lg text-charcoal-100 sm:text-xl">
              {section.label}
            </h4>
          ) : null}
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
            {section.deals.map((deal) => (
              <li key={deal.id} className="min-w-0">
                <DealCard {...deal} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
