"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { X } from "lucide-react";
import { NewsletterAuthIntro } from "@/components/newsletter/NewsletterAuthIntro";
import { NewsletterAuthPanel } from "@/components/newsletter/NewsletterAuthPanel";
import {
  NEWSLETTER_OPEN_EVENT,
  markNewsletterPopupDismissed,
  shouldShowNewsletterPopup,
} from "@/lib/newsletter-storage";

export function NewsletterPopup() {
  const [open, setOpen] = useState(false);
  const titleId = useId();

  useEffect(() => {
    if (!shouldShowNewsletterPopup()) return;
    const timer = window.setTimeout(() => setOpen(true), 1200);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    function onOpenRequest() {
      setOpen(true);
    }
    window.addEventListener(NEWSLETTER_OPEN_EVENT, onOpenRequest);
    return () => {
      window.removeEventListener(NEWSLETTER_OPEN_EVENT, onOpenRequest);
    };
  }, []);

  function dismiss() {
    markNewsletterPopupDismissed();
    setOpen(false);
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[300] flex items-end justify-center bg-black/40 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="Dismiss newsletter signup"
        onClick={dismiss}
      />
      <div className="relative z-10 w-full max-w-lg border border-charcoal-700 bg-white p-6 shadow-deal sm:p-8">
        <button
          type="button"
          onClick={dismiss}
          className="absolute right-3 top-3 rounded-md p-1.5 text-charcoal-400 transition hover:bg-burgundy-50 hover:text-burgundy-600"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>

        <NewsletterAuthIntro as="h2" titleId={titleId} className="pr-8" />

        <div className="mt-6">
          <NewsletterAuthPanel
            compact
            initialView="signup"
            onSuccess={() => {
              setOpen(false);
            }}
          />
        </div>

        <p className="mt-4 text-center text-xs text-charcoal-400">
          Prefer the full page?{" "}
          <Link
            href="/newsletter"
            className="text-burgundy-500 underline-offset-2 hover:underline"
            onClick={dismiss}
          >
            Open newsletter portal
          </Link>
        </p>
      </div>
    </div>
  );
}
