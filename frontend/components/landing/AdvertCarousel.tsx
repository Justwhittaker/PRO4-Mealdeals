"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { DealHeroMedia } from "@/components/deals/DealHeroMedia";
import type { Deal } from "@/lib/api";
import { formatMoney } from "@/lib/currency";

interface AdvertCarouselProps {
  deals: Deal[];
}

export function AdvertCarousel({ deals }: AdvertCarouselProps) {
  const [active, setActive] = useState(0);
  const count = deals.length;

  useEffect(() => {
    if (count < 2) return;
    const id = window.setInterval(() => {
      setActive((i) => (i + 1) % count);
    }, 5_000);
    return () => window.clearInterval(id);
  }, [count]);

  if (count === 0) {
    return (
      <div className="rounded-md border border-dashed border-charcoal-600 bg-white px-6 py-16 text-center shadow-sm">
        <p className="font-display text-2xl text-burgundy-500">
          Adverts loading soon
        </p>
        <p className="mt-2 text-sm text-charcoal-400">
          Merchant deals will rotate here throughout the day.
        </p>
      </div>
    );
  }

  function prev() {
    setActive((i) => (i - 1 + count) % count);
  }

  function next() {
    setActive((i) => (i + 1) % count);
  }

  return (
    <div className="relative mx-auto w-full max-w-5xl select-none">
      <button
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          prev();
        }}
        className="absolute left-0 top-1/2 z-40 -translate-y-1/2 rounded-md border border-charcoal-700 bg-white p-2 text-burgundy-600 shadow-sm transition hover:bg-burgundy-50 sm:-left-2"
        aria-label="Previous advert"
      >
        <ChevronLeft className="h-7 w-7" strokeWidth={2.5} />
      </button>
      <button
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          next();
        }}
        className="absolute right-0 top-1/2 z-40 -translate-y-1/2 rounded-md border border-charcoal-700 bg-white p-2 text-burgundy-600 shadow-sm transition hover:bg-burgundy-50 sm:-right-2"
        aria-label="Next advert"
      >
        <ChevronRight className="h-7 w-7" strokeWidth={2.5} />
      </button>

      <div className="relative mx-auto flex h-[340px] items-center justify-center perspective-[1200px] sm:h-[400px]">
        {deals.map((deal, index) => {
          let offset = index - active;
          if (offset > count / 2) offset -= count;
          if (offset < -count / 2) offset += count;

          const abs = Math.abs(offset);
          if (abs > 2) return null;

          const href = `/${deal.country}/${deal.city}/deals/${deal.id}`;
          const scale = abs === 0 ? 1 : abs === 1 ? 0.86 : 0.72;
          const rotateY = offset * -28;
          const translateX = offset * 38;
          const z = 30 - abs * 10;
          const opacity = abs === 0 ? 1 : abs === 1 ? 0.75 : 0.45;

          return (
            <Link
              key={deal.id}
              href={href}
              className={`absolute h-[280px] w-[200px] overflow-hidden rounded-sm border border-charcoal-700 bg-white shadow-deal transition-all duration-500 ease-out sm:h-[320px] sm:w-[230px] ${
                abs === 0 ? "" : "pointer-events-none"
              }`}
              style={{
                transform: `translateX(${translateX}%) rotateY(${rotateY}deg) scale(${scale})`,
                zIndex: z,
                opacity,
              }}
              tabIndex={abs === 0 ? 0 : -1}
              aria-hidden={abs !== 0}
            >
              <DealHeroMedia
                imageUrl={deal.imageUrl}
                logoUrl={deal.logoUrl}
                restaurantName={deal.restaurantName}
                aspectClassName="h-[55%] w-full"
              />
              <div className="space-y-1 p-3">
                <p className="truncate text-xs uppercase tracking-wider text-charcoal-400">
                  {deal.restaurantName}
                </p>
                <p className="line-clamp-2 font-display text-base leading-snug text-charcoal-50">
                  {deal.title}
                </p>
                <p className="pt-1 text-lg font-semibold text-burgundy-500">
                  {formatMoney(deal.price, deal.currency)}
                </p>
              </div>
            </Link>
          );
        })}
      </div>

      <div className="mt-4 flex justify-center gap-2">
        {deals.map((deal, index) => (
          <button
            key={deal.id}
            type="button"
            aria-label={`Show advert ${index + 1}`}
            onClick={() => setActive(index)}
            className={`h-2 w-2 rounded-full transition ${
              index === active ? "bg-burgundy-500" : "bg-charcoal-600"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
