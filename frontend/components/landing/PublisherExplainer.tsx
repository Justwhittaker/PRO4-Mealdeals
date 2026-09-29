import Link from "next/link";

interface PublisherExplainerProps {
  areaLabel?: string;
}

/**
 * Always-visible publisher copy for AdSense / crawlers.
 * Sits above the public deal grid on listing pages.
 */
export function PublisherExplainer({ areaLabel }: PublisherExplainerProps) {
  const where = areaLabel ? ` in ${areaLabel}` : " near you";

  return (
    <section
      className="mx-auto max-w-3xl px-1 py-8 sm:py-10"
      aria-labelledby="how-dine-a-deal-works"
    >
      <h2
        id="how-dine-a-deal-works"
        className="font-display text-2xl text-charcoal-50 sm:text-3xl"
      >
        How Dine A Deal works
      </h2>
      <div className="mt-4 space-y-3 text-sm leading-relaxed text-charcoal-300 sm:text-base">
        <p>
          Dine A Deal is a hospitality listings site for restaurants, cafés,
          bistros, hotels, bars, delis, and takeaways. We publish time-limited
          dining offers{where} — lunch sets, early-bird menus, hotel dining
          packages, and drinks promotions — so you can compare what is on this
          week without buying a voucher.
        </p>
        <p>
          Venues advertise on a flat-rate basis. There is no commission taken
          from the table when you redeem an offer; you book or walk in with the
          venue using the details on each listing. Priority subscriber deals
          sit above other listings so independent restaurants can stay visible
          next to larger groups.
        </p>
        <p>
          Browse by country and city, then filter by category (meals, wine and
          entertainment, hotels, groceries, bars, takeaway). A price is shown
          only when the venue states one. Otherwise the card names the offer
          type — lunch deal, happy hour, spend-and-save — and you confirm the
          details with the venue. Weekly Hot Deals is an optional email roundup.
          If a listing looks wrong, use the contact page.{" "}
          <Link
            href="/guides/how-we-list-offers"
            className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
          >
            How we list offers
          </Link>{" "}
          explains what each card means.
        </p>
      </div>
    </section>
  );
}
