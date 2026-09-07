"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { useMarketingConsent } from "@/components/cookie/CookieConsentProvider";
import { useNewsletterAccess } from "@/components/newsletter/useNewsletterAccess";
import {
  getAdSenseClientId,
  isAdSenseListingPath,
  isAdSenseLive,
} from "@/lib/adsense";

const SCRIPT_ATTR = "data-dineadeal-adsense";

function removeAdSenseScript(): void {
  document
    .querySelectorAll(`script[${SCRIPT_ATTR}]`)
    .forEach((node) => node.remove());
}

/**
 * Loads AdSense via a plain <script> in document.head (no next/script).
 * Avoids Next's data-nscript attribute that triggers:
 * "AdSense head tag doesn't support data-nscript attribute."
 *
 * Loads only when:
 * - marketing cookie consent is granted
 * - AdSense is live with manual slot IDs (no Auto ads)
 * - the route is a country/city listing page (not detail, forms, or auth)
 * - this device has joined the newsletter (ads sit beside public listings)
 */
export function AdSenseScript() {
  const pathname = usePathname();
  const marketingAllowed = useMarketingConsent();
  const { ready, unlocked } = useNewsletterAccess();
  const live = isAdSenseLive();
  const clientId = getAdSenseClientId();
  const onListing = isAdSenseListingPath(pathname);
  const allowScript =
    ready &&
    unlocked &&
    marketingAllowed &&
    live &&
    Boolean(clientId) &&
    onListing;

  useEffect(() => {
    if (!allowScript || !clientId) {
      removeAdSenseScript();
      return;
    }

    if (document.querySelector(`script[${SCRIPT_ATTR}]`)) {
      return;
    }

    const script = document.createElement("script");
    script.async = true;
    script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${clientId}`;
    script.crossOrigin = "anonymous";
    script.setAttribute(SCRIPT_ATTR, "1");
    document.head.appendChild(script);

    return () => {
      script.remove();
    };
  }, [allowScript, clientId]);

  return null;
}
