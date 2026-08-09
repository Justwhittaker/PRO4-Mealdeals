"use client";

import { Analytics } from "@vercel/analytics/next";
import { useCookieConsent } from "@/components/cookie/CookieConsentProvider";

/**
 * Loads Vercel Web Analytics only after analytics cookie consent.
 * Web Analytics itself is cookieless/anonymous; we still gate it to match
 * the site's analytics opt-in control.
 */
export function VercelAnalytics() {
  const { analyticsAllowed } = useCookieConsent();
  if (!analyticsAllowed) return null;
  return <Analytics />;
}
