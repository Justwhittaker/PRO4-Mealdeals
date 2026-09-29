import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { publicPageMetadata } from "@/lib/seo";

export const metadata: Metadata = publicPageMetadata({
  title: "How we list offers",
  description:
    "How to read a Dine A Deal listing, when a price is shown, and how to report an offer that looks wrong.",
  path: "/guides/how-we-list-offers",
});

export default function HowWeListOffersPage() {
  return (
    <div className="relative min-h-screen bg-white">
      <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
          Guide
        </p>
        <h1 className="mt-2 font-display text-3xl text-charcoal-50 sm:text-4xl">
          How we list offers
        </h1>
        <p className="mt-4 text-sm leading-relaxed text-charcoal-300 sm:text-base">
          Dine A Deal is a city-by-city directory of hospitality offers. This
          page explains what you are looking at, so a card is easy to judge
          before you visit.
        </p>

        <section className="mt-10" aria-labelledby="card-heading">
          <h2
            id="card-heading"
            className="font-display text-2xl text-charcoal-50"
          >
            What is on a card
          </h2>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-relaxed text-charcoal-300 sm:text-base">
            <li>The venue name and the city or neighbourhood.</li>
            <li>
              The offer type: lunch meal deal, breakfast bundle, hot meal,
              happy hour, takeaway deal, or grocery spend-and-save.
            </li>
            <li>
              A price only when the venue has published one. A crossed-out
              price appears only when the venue states a real comparison, such
              as a percent off.
            </li>
            <li>
              A link to the venue. Opening that link asks you to join Weekly
              Hot Deals first; browsing the directory itself does not.
            </li>
          </ul>
        </section>

        <section className="mt-10" aria-labelledby="check-heading">
          <h2
            id="check-heading"
            className="font-display text-2xl text-charcoal-50"
          >
            Check before you go
          </h2>
          <div className="mt-4 space-y-4 text-sm leading-relaxed text-charcoal-300 sm:text-base">
            <p>
              Offer hours and inclusions change. The listing tells you the kind
              of promotion to ask about. The venue confirms whether it is on
              today, what it includes, and what it costs.
            </p>
            <p>
              Priority listings are written by the restaurant that pays for a
              flat-rate placement. Other listings are short summaries we
              prepare so a venue&apos;s homepage title is not shown as if it
              were the offer. We do not invent a &quot;was&quot; price from
              unrelated numbers on a page.
            </p>
          </div>
        </section>

        <section className="mt-10" aria-labelledby="categories-heading">
          <h2
            id="categories-heading"
            className="font-display text-2xl text-charcoal-50"
          >
            Categories
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-charcoal-300 sm:text-base">
            Filters group venues into restaurants and cafés, takeaway, wine and
            entertainment, delis and grocers, bars and pubs, and hotels. A
            grocery card is a spend-and-save or shop discount, not a plated
            lunch. A bar card is a happy hour or drink special.
          </p>
        </section>

        <section className="mt-10" aria-labelledby="report-heading">
          <h2
            id="report-heading"
            className="font-display text-2xl text-charcoal-50"
          >
            Report a listing
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-charcoal-300 sm:text-base">
            Write to us from the{" "}
            <Link
              href="/contact"
              className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
            >
              contact page
            </Link>{" "}
            if a venue is in the wrong city, the offer has ended, or the page
            should come down. See also the{" "}
            <Link
              href="/about"
              className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
            >
              about page
            </Link>
            ,{" "}
            <Link
              href="/privacy"
              className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
            >
              privacy notice
            </Link>
            , and{" "}
            <Link
              href="/cookies"
              className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
            >
              cookie policy
            </Link>
            .
          </p>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
