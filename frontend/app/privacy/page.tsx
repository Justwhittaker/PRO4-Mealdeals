import Link from "next/link";
import { SiteFooter } from "@/components/landing/SiteFooter";

export const metadata = {
  title: "Privacy Notice",
  description:
    "Privacy Notice for CheddaCheeze T/A Dine A Deal — including third-party marketing and compensated data sharing.",
};

export default function PrivacyNoticePage() {
  return (
    <div className="min-h-screen bg-white">
      <main className="mx-auto max-w-2xl px-4 py-12 sm:px-6 sm:py-16">
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
          Legal
        </p>
        <h1 className="mt-2 font-display text-3xl text-charcoal-50 sm:text-4xl">
          Privacy Notice
        </h1>
        <p className="mt-3 text-sm text-charcoal-300">
          CheddaCheeze T/A Dine A Deal · Last updated 8 August 2026
        </p>

        <nav
          className="mt-6 flex flex-wrap gap-x-4 gap-y-2 text-sm text-burgundy-600"
          aria-label="Privacy sections"
        >
          <a href="#third-party-marketing" className="hover:underline">
            Third-party marketing
          </a>
          <Link href="/privacy/partners" className="hover:underline">
            Partner information
          </Link>
          <Link href="/privacy/choices" className="hover:underline">
            Privacy Choices
          </Link>
        </nav>

        <article className="mt-10 space-y-6 text-sm leading-relaxed text-charcoal-200">
          <section id="third-party-marketing" className="scroll-mt-24">
            <h2 className="font-display text-xl text-charcoal-50 sm:text-2xl">
              Third-party marketing and compensated data sharing
            </h2>

            <p className="mt-4">
              Where you separately choose to participate, CheddaCheeze T/A
              DineADeal may disclose, license or sell certain personal
              information to third-party businesses for their own marketing
              purposes.
            </p>

            <p className="mt-4">The information involved may include:</p>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>your name;</li>
              <li>your email address;</li>
              <li>your country or general region;</li>
              <li>
                preferences or interests that you voluntarily provide; and
              </li>
              <li>the date, source and scope of your permission.</li>
            </ul>

            <p className="mt-4">
              We may receive money, services or another commercial benefit in
              connection with these disclosures.
            </p>

            <p className="mt-4">
              Recipients may include businesses operating in the following
              categories:
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>retail and consumer products;</li>
              <li>restaurants, hospitality and travel;</li>
              <li>entertainment and events;</li>
              <li>technology and digital services;</li>
              <li>advertising and marketing;</li>
              <li>competitions and promotional offers; and</li>
              <li>market research.</li>
            </ul>

            <p className="mt-4">
              A current description of the categories of recipients, and where
              required the identity of individual recipients, is available at{" "}
              <Link
                href="/privacy/partners"
                className="text-burgundy-600 underline-offset-2 hover:underline"
              >
                Partner information
              </Link>
              .
            </p>

            <p className="mt-4">
              Third parties receiving your information may use it to contact you
              by email about their own products, services, promotions, surveys
              or offers. They may act as independent controllers of your
              information and will process it under their own privacy notices.
            </p>

            <p className="mt-4">
              We will not disclose your information for third-party marketing
              unless you have selected the relevant optional permission, or
              another applicable legal basis clearly permits the disclosure.
            </p>

            <p className="mt-4">
              You may withdraw your permission or request that we stop future
              sale or sharing at any time by:
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>
                selecting{" "}
                <Link
                  href="/privacy/choices"
                  className="text-burgundy-600 underline-offset-2 hover:underline"
                >
                  Privacy Choices
                </Link>{" "}
                on our website;
              </li>
              <li>using the unsubscribe or privacy link in an email.</li>
            </ul>

            <p className="mt-4">
              Withdrawal will not affect disclosures lawfully completed before
              the request was processed. We will stop future disclosures and
              take any additional steps required by applicable law.
            </p>

            <p className="mt-4">
              We retain records of your permission for 5 years so that we can
              demonstrate and administer your privacy choices. Further
              information about retention, international transfers and your
              privacy rights is provided elsewhere in this Privacy Notice.
            </p>
          </section>
        </article>

        <p className="mt-12 text-center text-sm text-charcoal-400">
          <Link href="/privacy/choices" className="text-burgundy-600 hover:underline">
            Privacy Choices
          </Link>
          {" · "}
          <Link href="/contact" className="text-burgundy-600 hover:underline">
            Contact
          </Link>
          {" · "}
          <Link href="/" className="text-burgundy-600 hover:underline">
            Home
          </Link>
        </p>
      </main>
      <SiteFooter />
    </div>
  );
}
