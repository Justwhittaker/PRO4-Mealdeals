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
    <div className="relative min-h-screen bg-white">
      <main className="hero-atmosphere grain relative border-b border-charcoal-700">
        <div className="relative z-10 mx-auto max-w-lg px-4 py-12 sm:px-6 sm:py-16">
          <div className="border border-charcoal-700 bg-white/90 p-6 shadow-deal sm:p-8">
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
