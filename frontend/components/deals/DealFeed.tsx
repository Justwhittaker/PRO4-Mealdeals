import type { ReactNode } from "react";
import { DealCard, type DealCardProps } from "@/components/deals/DealCard";
import { InFeedAd } from "@/components/ads/InFeedAd";
import { SidebarAd } from "@/components/ads/SidebarAd";
import {
  getAdSenseSidebarSlotId,
  isAdSenseLive,
} from "@/lib/adsense";
import { rankDeals } from "@/lib/priority";

interface DealFeedProps {
  deals: DealCardProps[];
  emptyMessage?: string;
  showSidebarAd?: boolean;
  /** When true, keep API order (e.g. nearest-first). */
  preserveOrder?: boolean;
}

export function DealFeed({
  deals,
  emptyMessage = "No deals found in this area yet.",
  showSidebarAd = true,
  preserveOrder = false,
}: DealFeedProps) {
  const ranked = preserveOrder ? deals : rankDeals(deals);

  if (ranked.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-charcoal-700 bg-charcoal-900/40 px-6 py-16 text-center">
        <p className="font-display text-xl text-charcoal-200">{emptyMessage}</p>
        <p className="mt-2 text-sm text-charcoal-500">
          Check back soon or explore a nearby city.
        </p>
      </div>
    );
  }

  const items: ReactNode[] = [];
  const denseEnoughForAds = ranked.length >= 8;
  ranked.forEach((deal, index) => {
    items.push(<DealCard key={deal.id} {...deal} />);
    if (
      denseEnoughForAds &&
      (index + 1) % 5 === 0 &&
      index + 1 < ranked.length
    ) {
      items.push(<InFeedAd key={`ad-${index}`} />);
    }
  });

  const sidebar =
    showSidebarAd && denseEnoughForAds && isAdSenseLive() && getAdSenseSidebarSlotId();

  return (
    <div
      className={
        sidebar ? "grid gap-8 lg:grid-cols-[1fr_280px]" : undefined
      }
    >
      <div className="grid gap-5 sm:grid-cols-2">{items}</div>
      {sidebar ? (
        <div className="hidden lg:block">
          <SidebarAd />
        </div>
      ) : null}
    </div>
  );
}
