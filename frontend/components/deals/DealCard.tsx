import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { DealHeroMedia } from "@/components/deals/DealHeroMedia";
import {
  categorizeVenue,
  parentCategoryLabel,
} from "@/lib/categories";
import { formatMoney, type CurrencyCode } from "@/lib/currency";
import { dealBadge, type TierLevel } from "@/lib/priority";
import { formatDistanceMiles } from "@/lib/radius";

export interface DealCardProps {
  id: string;
  title: string;
  restaurantName: string;
  price: number;
  originalPrice?: number | null;
  currency: CurrencyCode;
  country: string;
  city: string;
  tier: TierLevel;
  isSubscriber?: boolean;
  isScraped?: boolean;
  imageUrl?: string | null;
  logoUrl?: string | null;
  savingsPercent?: number;
  createdAt: string;
  distanceKm?: number | null;
}

export function DealCard(deal: DealCardProps) {
  const badge = dealBadge(deal);
  const href = `/${deal.country}/${deal.city}/deals/${deal.id}`;
  const venueCategory = parentCategoryLabel(categorizeVenue(deal.restaurantName));

  return (
    <Card className="group overflow-hidden rounded-sm border border-charcoal-600 bg-white shadow-deal transition duration-300 hover:-translate-y-0.5 hover:border-burgundy-300">
      <Link href={href} className="block">
        <div className="relative">
          <DealHeroMedia
            imageUrl={deal.imageUrl}
            logoUrl={deal.logoUrl}
            restaurantName={deal.restaurantName}
            aspectClassName="aspect-[16/10]"
            hoverZoom
          />
          {badge ? (
            <div className="absolute left-3 top-3 z-10">
              <Badge variant={badge.variant}>{badge.label}</Badge>
            </div>
          ) : null}
          <div className="absolute right-3 top-3 z-10 max-w-[70%] truncate rounded-md bg-charcoal-900/80 px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-charcoal-200">
            {venueCategory}
          </div>
          {deal.savingsPercent && deal.savingsPercent > 0 ? (
            <div className="absolute bottom-3 right-3 z-10 rounded-md bg-burgundy-500 px-2 py-1 text-xs font-semibold text-white">
              Save {deal.savingsPercent}%
            </div>
          ) : null}
        </div>
        <CardContent className="space-y-2 p-4">
          <p className="text-xs uppercase tracking-wider text-charcoal-400">
            {deal.restaurantName}
            {deal.city ? ` · ${deal.city.replace(/-/g, " ")}` : ""}
            {formatDistanceMiles(deal.distanceKm)
              ? ` · ${formatDistanceMiles(deal.distanceKm)}`
              : ""}
          </p>
          <h3 className="line-clamp-2 font-display text-lg leading-snug text-charcoal-50">
            {deal.title}
          </h3>
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-semibold text-burgundy-500">
              {formatMoney(deal.price, deal.currency)}
            </span>
            {deal.originalPrice && deal.originalPrice > deal.price ? (
              <span className="text-sm text-charcoal-500 line-through">
                {formatMoney(deal.originalPrice, deal.currency)}
              </span>
            ) : null}
          </div>
        </CardContent>
      </Link>
    </Card>
  );
}
