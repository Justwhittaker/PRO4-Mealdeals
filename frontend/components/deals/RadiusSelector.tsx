"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CategorySelector } from "@/components/deals/CategorySelector";
import { parseCategoryParam, type ParentCategoryId } from "@/lib/categories";
import {
  RADIUS_OPTIONS,
  parseFeedSort,
  parseRadiusMiles,
  type FeedSort,
  type RadiusMiles,
} from "@/lib/radius";

interface RadiusSelectorProps {
  radius: RadiusMiles;
  sort?: FeedSort;
  category?: ParentCategoryId | "all";
  /** Geo listings are country-wide — hide radius so it cannot shrink the set. */
  showRadius?: boolean;
  showSort?: boolean;
  showCategory?: boolean;
}

export function RadiusSelector({
  radius,
  sort = "score",
  category = "all",
  showRadius = true,
  showSort = true,
  showCategory = true,
}: RadiusSelectorProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const sortValue = searchParams.has("sort")
    ? parseFeedSort(searchParams.get("sort"))
    : sort;
  const radiusValue = searchParams.has("radius")
    ? parseRadiusMiles(searchParams.get("radius"))
    : radius;
  const categoryValue = searchParams.has("category")
    ? parseCategoryParam(searchParams.get("category"))
    : category;

  function pushParams(patch: Record<string, string>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(patch)) {
      params.set(key, value);
    }
    params.delete("page");
    router.push(`${pathname}?${params.toString()}`);
  }

  const sortSelect = showSort ? (
    <div className="w-[160px]">
      <Select
        value={sortValue}
        onValueChange={(next) => pushParams({ sort: next })}
      >
        <SelectTrigger aria-label="Sort deals">
          <SelectValue placeholder="Sort" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="score">Featured first</SelectItem>
          <SelectItem value="distance">Nearest first</SelectItem>
        </SelectContent>
      </Select>
    </div>
  ) : null;

  const radiusSelect = showRadius ? (
    <div className="w-[150px]">
      <Select
        value={String(radiusValue)}
        onValueChange={(next) => pushParams({ radius: next })}
      >
        <SelectTrigger aria-label="Search radius">
          <SelectValue placeholder="Radius" />
        </SelectTrigger>
        <SelectContent>
          {RADIUS_OPTIONS.map((miles) => (
            <SelectItem key={miles} value={String(miles)}>
              {miles} miles
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  ) : null;

  const onlyInlineFilters = !showCategory && (showRadius || showSort);

  return (
    <div
      className={
        onlyInlineFilters
          ? "inline-flex items-center gap-2"
          : "flex w-full max-w-md flex-col items-stretch gap-2 sm:max-w-none sm:items-center"
      }
    >
      {showCategory ? <CategorySelector category={categoryValue} /> : null}
      {radiusSelect || sortSelect ? (
        <div className="flex flex-wrap items-center justify-center gap-2">
          {radiusSelect}
          {sortSelect}
        </div>
      ) : null}
    </div>
  );
}
