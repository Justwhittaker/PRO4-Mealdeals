"use client";

import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { useNewsletterAccess } from "@/components/newsletter/useNewsletterAccess";
import { openNewsletterSignup } from "@/lib/newsletter-storage";

interface NewsletterDealGateProps {
  children: ReactNode;
  /** Optional compact layout for detail pages. */
  compact?: boolean;
}

/**
 * Deal listings always render in the HTML (SSR + first paint) so crawlers
 * and AdSense reviewers see real inventory. Unsigned visitors still get a
 * signup banner and the newsletter popup — the grid is no longer replaced.
 */
export function NewsletterDealGate({
  children,
  compact = false,
}: NewsletterDealGateProps) {
  const { ready, unlocked } = useNewsletterAccess();
  const showBanner = ready && !unlocked;

  return (
    <div>
      {showBanner ? (
        <div
          className={
            compact
              ? "mb-6 rounded-md border border-charcoal-700 bg-white px-4 py-5 text-center shadow-sm"
              : "mb-8 rounded-md border border-charcoal-700 bg-white px-6 py-6 text-center shadow-sm"
          }
          role="region"
          aria-label="Weekly Hot Deals newsletter"
        >
          <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
            Weekly Hot Deals
          </p>
          <h2 className="mt-2 font-display text-xl text-charcoal-50 sm:text-2xl">
            Get the weekly roundup in your inbox
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-charcoal-300">
            Listings below are public. Sign up to open deal links and get the
            weekly roundup for your city.
          </p>
          <Button
            type="button"
            className="mt-4"
            onClick={() => openNewsletterSignup()}
          >
            Sign up for the newsletter
          </Button>
        </div>
      ) : null}
      {children}
    </div>
  );
}
