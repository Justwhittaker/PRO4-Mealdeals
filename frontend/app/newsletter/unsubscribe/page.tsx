import { Suspense } from "react";
import { UnsubscribeClient } from "@/components/newsletter/UnsubscribeClient";
import { SiteFooter } from "@/components/landing/SiteFooter";

export const metadata = {
  title: "Unsubscribe from Weekly Hot Deals",
};

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
