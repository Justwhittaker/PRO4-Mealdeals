"use client";

import { Button } from "@/components/ui/button";
import { useNewsletterAccess } from "@/components/newsletter/useNewsletterAccess";
import {
  openNewsletterSignup,
  setPendingGoDealId,
} from "@/lib/newsletter-storage";

interface DealGoCtaProps {
  dealId: string;
  label: string;
  variant?: "button" | "link";
}

/**
 * Outbound deal CTA. Listings stay public; /go requires newsletter unlock.
 */
export function DealGoCta({
  dealId,
  label,
  variant = "button",
}: DealGoCtaProps) {
  const { unlocked } = useNewsletterAccess();

  function requireSignup() {
    setPendingGoDealId(dealId);
    openNewsletterSignup();
  }

  if (unlocked) {
    if (variant === "link") {
      return (
        <a
          href={`/go/${dealId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-burgundy-600 underline-offset-2 hover:underline break-all"
        >
          {label}
        </a>
      );
    }
    return (
      <Button asChild size="lg">
        <a href={`/go/${dealId}`} target="_blank" rel="noopener noreferrer">
          {label}
        </a>
      </Button>
    );
  }

  if (variant === "link") {
    return (
      <button
        type="button"
        onClick={requireSignup}
        className="font-medium text-burgundy-600 underline-offset-2 hover:underline break-all"
      >
        {label}
      </button>
    );
  }

  return (
    <div className="space-y-1">
      <Button type="button" size="lg" onClick={requireSignup}>
        {label}
      </Button>
      <p className="text-xs text-charcoal-400">
        Sign up for Weekly Hot Deals to open this offer.
      </p>
    </div>
  );
}
