import { NewsletterPortalClient } from "@/components/newsletter/NewsletterPortalClient";
import { SiteFooter } from "@/components/landing/SiteFooter";

export const metadata = {
  title: "Weekly Hot Deals newsletter",
  description:
    "Sign up for Dine A Deal Weekly Hot Deals. First name, surname, email, and location — unsubscribe anytime without erasing your details.",
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
    <div className="relative min-h-screen bg-white">
      <main className="hero-atmosphere grain relative border-b border-charcoal-700">
        <div className="relative z-10 mx-auto max-w-lg px-4 py-12 sm:px-6 sm:py-16">
          <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
            Customer newsletter
          </p>
          <h1 className="mt-2 font-display text-3xl text-charcoal-50 sm:text-4xl">
            Weekly Hot Deals newsletter
          </h1>
          <p className="mt-3 text-sm text-charcoal-300">
            Sign up with your first name, surname, email, and location.
            Unsubscribe links pause emails — your record stays so you can
            subscribe again anytime.
          </p>
          <div className="mt-8 border border-charcoal-700 bg-white/90 p-6 shadow-deal">
            <NewsletterPortalClient
              resubscribe={resubscribe}
              token={token}
              initialEmail={email}
            />
          </div>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
