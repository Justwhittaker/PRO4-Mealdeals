"use client";

import { useEffect, useId, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import type { ConsentState } from "@/lib/cookie-consent";

interface CookieSettingsProps {
  consent: ConsentState;
  onClose: () => void;
  onSave: (choices: { analytics: boolean; marketing: boolean }) => void;
  onAcceptAll: () => void;
  onReject: () => void;
}

export function CookieSettings({
  consent,
  onClose,
  onSave,
  onAcceptAll,
  onReject,
}: CookieSettingsProps) {
  const titleId = useId();
  const [analytics, setAnalytics] = useState(consent.analytics);
  const [marketing, setMarketing] = useState(consent.marketing);

  useEffect(() => {
    setAnalytics(consent.analytics);
    setMarketing(consent.marketing);
  }, [consent.analytics, consent.marketing]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-[70] flex items-end justify-center bg-black/40 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="Close cookie settings"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-md border border-charcoal-700 bg-white p-5 shadow-deal sm:p-6">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 rounded-md p-1.5 text-charcoal-400 transition hover:bg-burgundy-50 hover:text-burgundy-600"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>

        <h2
          id={titleId}
          className="pr-8 font-display text-2xl text-charcoal-50"
        >
          Cookie settings
        </h2>
        <p className="mt-2 text-sm text-charcoal-300">
          Choose which optional cookies we may use. Necessary cookies stay on
          so the site works.
        </p>

        <ul className="mt-5 space-y-4">
          <li className="rounded-md border border-charcoal-700 bg-charcoal-950/40 px-3 py-3">
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor="cookie-necessary" className="text-sm text-charcoal-100">
                Necessary
              </Label>
              <input
                id="cookie-necessary"
                type="checkbox"
                checked
                disabled
                className="h-4 w-4 rounded border-charcoal-600"
              />
            </div>
            <p className="mt-1 text-xs text-charcoal-400">
              Auth, security, and essential preferences such as your location.
            </p>
          </li>

          <li className="rounded-md border border-charcoal-700 px-3 py-3">
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor="cookie-analytics" className="text-sm text-charcoal-100">
                Analytics
              </Label>
              <input
                id="cookie-analytics"
                type="checkbox"
                checked={analytics}
                onChange={(e) => setAnalytics(e.target.checked)}
                className="h-4 w-4 rounded border-charcoal-600 text-burgundy-600 focus:ring-burgundy-500/40"
              />
            </div>
            <p className="mt-1 text-xs text-charcoal-400">
              Helps us understand how the site is used so we can improve it.
            </p>
          </li>

          <li className="rounded-md border border-charcoal-700 px-3 py-3">
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor="cookie-marketing" className="text-sm text-charcoal-100">
                Marketing
              </Label>
              <input
                id="cookie-marketing"
                type="checkbox"
                checked={marketing}
                onChange={(e) => setMarketing(e.target.checked)}
                className="h-4 w-4 rounded border-charcoal-600 text-burgundy-600 focus:ring-burgundy-500/40"
              />
            </div>
            <p className="mt-1 text-xs text-charcoal-400">
              Advertising cookies (including Google AdSense) to show and measure
              ads.
            </p>
          </li>
        </ul>

        <div className="mt-5 flex flex-col gap-2">
          <Button
            type="button"
            onClick={() => onSave({ analytics, marketing })}
          >
            Save choices
          </Button>
          <Button type="button" variant="outline" onClick={onReject}>
            Reject non-essential
          </Button>
          <Button type="button" variant="secondary" onClick={onAcceptAll}>
            Accept all
          </Button>
        </div>
      </div>
    </div>
  );
}
