"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  PARENT_CATEGORIES,
  type ParentCategoryId,
} from "@/lib/categories";

interface CategorySelectorProps {
  category: ParentCategoryId | "all";
  /** Match landing search inputs (taller, white). */
  variant?: "default" | "hero";
  className?: string;
}

export function CategorySelector({
  category,
  variant = "default",
  className = "",
}: CategorySelectorProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function onChange(next: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "all") {
      params.delete("category");
    } else {
      params.set("category", next);
    }
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  }

  return (
    <div
      className={
        className ||
        (variant === "hero" ? "w-full" : "w-full max-w-md")
      }
    >
      <Select value={category} onValueChange={onChange}>
        <SelectTrigger
          aria-label="Venue category"
          className={
            variant === "hero"
              ? "h-12 border-charcoal-600 bg-white text-base text-charcoal-100 shadow-sm"
              : undefined
          }
        >
          <SelectValue placeholder="Category" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All categories</SelectItem>
          {PARENT_CATEGORIES.map((c) => (
            <SelectItem key={c.id} value={c.id}>
              {c.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
