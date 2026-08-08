"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

interface CookieBannerProps {
  onAcceptAll: () => void;
  onReject: () => void;
  onCustomize: () => void;
}

export function CookieBanner({
  onAcceptAll,
  onReject,
  onCustomize,
}: CookieBannerProps) {
  return (
    <div
      className="fixed inset-x-0 bottom-0 z-[60] border-t border-charcoal-700 bg-white p-4 shadow-deal sm:p-5"
      role="dialog"
      aria-labelledby="cookie-banner-title"
      aria-describedby="cookie-banner-body"
    >
      <div className="mx-auto flex max-w-4xl flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0 space-y-1.5">
          <p
            id="cookie-banner-title"
            className="font-display text-lg text-charcoal-50"
          >
            Cookie preferences
          </p>
          <p
            id="cookie-banner-body"
            className="text-sm leading-relaxed text-charcoal-300"
          >
            We use necessary cookies to run the site. Optional analytics and
            marketing cookies help us improve and measure ads — only with your
            permission. See our{" "}
            <Link
              href="/privacy"
              className="text-burgundy-600 underline-offset-2 hover:underline"
            >
              Privacy Notice
            </Link>
            .
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:min-w-[16rem]">
          <Button type="button" variant="outline" onClick={onReject}>
            Reject non-essential
          </Button>
          <Button type="button" variant="secondary" onClick={onCustomize}>
            Customize
          </Button>
          <Button type="button" onClick={onAcceptAll}>
            Accept all
          </Button>
        </div>
      </div>
    </div>
  );
}
