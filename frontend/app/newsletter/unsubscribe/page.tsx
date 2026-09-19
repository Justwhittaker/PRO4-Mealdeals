import { Suspense } from "react";
import type { Metadata } from "next";
import { UnsubscribeClient } from "@/components/newsletter/UnsubscribeClient";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { publicPageMetadata } from "@/lib/seo";

export const metadata: Metadata = publicPageMetadata({
  title: "Unsubscribe from Weekly Hot Deals",
  description:
    "Unsubscribe from the Dine A Deal Weekly Hot Deals newsletter.",
  path: "/newsletter/unsubscribe",
  index: false,
});

export default function NewsletterUnsubscribePage() {
  return (
    <div className="relative min-h-screen bg-white">
      <main className="mx-auto max-w-lg px-4 py-16 sm:px-6">
        <h1 className="font-display text-3xl text-charcoal-50">
          Unsubscribe
        </h1>
        <Suspense
          fallback={
            <p className="mt-4 text-sm text-charcoal-300">
              Updating preferences…
            </p>
          }
        >
          <UnsubscribeClient />
        </Suspense>
      </main>

      <SiteFooter />
    </div>
  );
}
