"use client";

import { useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  NEWSLETTER_ACCESS_EVENT,
  isNewsletterSubscribedLocally,
  openNewsletterSignup,
} from "@/lib/newsletter-storage";

function subscribeNewsletterAccess(onStoreChange: () => void): () => void {
  window.addEventListener(NEWSLETTER_ACCESS_EVENT, onStoreChange);
  window.addEventListener("storage", onStoreChange);
  return () => {
    window.removeEventListener(NEWSLETTER_ACCESS_EVENT, onStoreChange);
    window.removeEventListener("storage", onStoreChange);
  };
}

function getNewsletterAccessSnapshot(): boolean {
  return isNewsletterSubscribedLocally();
}

function getNewsletterAccessServerSnapshot(): boolean {
  return false;
}

interface NewsletterDealGateProps {
  children: ReactNode;
  /** Optional compact layout for detail pages. */
  compact?: boolean;
}

/**
 * Locks deal inventory until the visitor is a newsletter reader on this device.
 * Dismissing the popup does not unlock — only signup / sign-in does.
 */
export function NewsletterDealGate({
  children,
  compact = false,
}: NewsletterDealGateProps) {
  const [ready, setReady] = useState(false);
  const unlocked = useSyncExternalStore(
    subscribeNewsletterAccess,
    getNewsletterAccessSnapshot,
    getNewsletterAccessServerSnapshot,
  );

  useEffect(() => {
    setReady(true);
  }, []);

  // Avoid flashing the lock CTA for returning subscribers during hydration.
  if (!ready) {
    return (
      <div
        className={
          compact ? "min-h-[12rem]" : "mx-auto min-h-[16rem] max-w-xl"
        }
        aria-busy="true"
      />
    );
  }

  if (unlocked) return <>{children}</>;

  return (
    <div
      className={
        compact
          ? "rounded-md border border-charcoal-700 bg-white px-6 py-10 text-center shadow-sm"
          : "mx-auto max-w-xl rounded-md border border-charcoal-700 bg-white px-6 py-14 text-center shadow-sm"
      }
      role="region"
      aria-label="Newsletter required"
    >
      <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
        Weekly Hot Deals
      </p>
      <h2 className="mt-2 font-display text-2xl text-charcoal-50 sm:text-3xl">
        Newsletter signup required
      </h2>
      <p className="mt-3 text-sm leading-relaxed text-charcoal-300 sm:text-base">
        To see your hot new deals in your area, make sure you sign up for the
        newsletter.
      </p>
      <Button
        type="button"
        className="mt-6"
        onClick={() => openNewsletterSignup()}
      >
        Sign up for the newsletter
      </Button>
      <p className="mt-3 text-xs text-charcoal-400">
        Already subscribed? Use Sign in in the popup or the mail icon in the
        header.
      </p>
    </div>
  );
}
