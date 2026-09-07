import { NewsletterPortalClient } from "@/components/newsletter/NewsletterPortalClient";
import { SiteFooter } from "@/components/landing/SiteFooter";

export const metadata = {
  title: "Weekly Hot Deals newsletter",
  description:
    "Sign up or sign in for Dine A Deal Weekly Hot Deals. New readers join with name, email, and location; returning readers sign in with email on a new device.",
};

export default function NewsletterPortalPage({
  searchParams,
}: {
  searchParams?: { resubscribe?: string; token?: string; email?: string };
}) {
  const resubscribe = searchParams?.resubscribe === "1";
  const token = searchParams?.token;
  const email = searchParams?.email ?? "";

  return (
    <div className="relative min-h-screen max-w-[100vw] overflow-x-clip bg-white">
      <main className="hero-atmosphere grain relative w-full border-b border-charcoal-700">
        <div className="relative z-10 mx-auto flex w-full max-w-3xl justify-center px-3 py-10 sm:px-6 sm:py-16">
          {/* Single card: intro + Sign up / Returning reader CTAs all live inside. */}
          <div className="w-full rounded-md border border-charcoal-700 bg-white p-5 shadow-deal sm:p-8">
            <NewsletterPortalClient
              resubscribe={resubscribe}
              token={token}
              initialEmail={email}
            />
          </div>
        </div>
      </main>

      <section
        className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14"
        aria-labelledby="newsletter-what-you-get"
      >
        <h2
          id="newsletter-what-you-get"
          className="font-display text-2xl text-charcoal-50 sm:text-3xl"
        >
          What Weekly Hot Deals includes
        </h2>
        <div className="mt-4 space-y-3 text-sm leading-relaxed text-charcoal-300 sm:text-base">
          <p>
            Weekly Hot Deals is the optional email roundup for Dine A Deal
            readers. After you sign up (or sign in on a new device), we remember
            your city on this browser and send featured restaurant, hotel, and
            bar offers — meals, wine and entertainment, hotels, groceries,
            bars, and takeaway.
          </p>
          <p>
            Listings on the site are public to browse. The newsletter is extra:
            a weekly digest near the location you choose. You can unsubscribe
            from any email or from this portal. We do not sell a voucher; you
            redeem with the venue using the details on each listing. Ads, when
            shown, only appear beside deal grids on listing pages — never on
            this signup screen.
          </p>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
