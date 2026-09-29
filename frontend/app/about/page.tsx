import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { publicPageMetadata } from "@/lib/seo";

export const metadata: Metadata = publicPageMetadata({
  title: "About us",
  description:
    "Dine A Deal is a dining-offers directory run by CheddaCheeze. Venues advertise at a flat rate, and readers compare lunch, happy hour, and grocery offers before they visit.",
  path: "/about",
});

export default function AboutPage() {
  return (
    <div className="relative min-h-screen bg-white">
      <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
          Dine a Deal
        </p>
        <h1 className="mt-2 font-display text-3xl text-charcoal-50 sm:text-4xl">
          About us
        </h1>
        <div className="mt-4 space-y-4 text-sm leading-relaxed text-charcoal-300 sm:text-base">
          <p>
            Dine A Deal is a directory of dining offers for restaurants, cafés,
            bars, hotels, and grocers. CheddaCheeze trades as Dine A Deal and
            publishes the site so you can see what is on this week in a city
            before you book or walk in.
          </p>
          <p>
            Venues that want a featured placement buy Priority advertising at a
            flat rate. We do not take a cut of the bill, and we do not sell
            vouchers. You redeem an offer with the venue, using the details on
            the listing.
          </p>
        </div>

        <section className="mt-12" aria-labelledby="listings-heading">
          <h2
            id="listings-heading"
            className="font-display text-2xl text-charcoal-50"
          >
            What a listing is
          </h2>
          <div className="mt-4 space-y-4 text-sm leading-relaxed text-charcoal-300 sm:text-base">
            <p>
              Each card names the venue, the city, and the kind of offer: a
              lunch deal, breakfast bundle, happy hour, takeaway promotion, or
              grocery spend-and-save. A price appears only when that venue has
              published one. If we cannot confirm a was/now price, we leave the
              money off the card rather than guess.
            </p>
            <p>
              Priority listings are written by the venue. Other listings are
              short summaries we prepare from the venue&apos;s own offer pages,
              rewritten into a consistent format so a homepage title is not
              presented as a deal. Always confirm today&apos;s inclusions with
              the restaurant before you go — menus change.
            </p>
            <p>
              <Link
                href="/guides/how-we-list-offers"
                className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
              >
                How we list offers
              </Link>{" "}
              walks through the card, the categories, and how to tell us when
              something is wrong.
            </p>
          </div>
        </section>

        <section className="mt-12" aria-labelledby="correct-heading">
          <h2
            id="correct-heading"
            className="font-display text-2xl text-charcoal-50"
          >
            Correct a listing
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-charcoal-300 sm:text-base">
            If a name, city, or offer looks wrong, or you want a listing
            removed, write to us from the{" "}
            <Link
              href="/contact"
              className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
            >
              contact page
            </Link>
            . We reply from just.whittaker@gmail.com. Privacy choices, cookies,
            and the terms of use are linked in the footer.
          </p>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
