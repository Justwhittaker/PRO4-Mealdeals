"use client";

import { useEffect } from "react";
import {
  getAdSenseClientId,
  isAdSenseLive,
} from "@/lib/adsense";
import { useMarketingConsent } from "@/components/cookie/CookieConsentProvider";

const SCRIPT_ATTR = "data-dineadeal-adsense";

/**
 * Loads AdSense via a plain <script> in document.head (no next/script).
 * Avoids Next's data-nscript attribute that triggers:
 * "AdSense head tag doesn't support data-nscript attribute."
 *
 * Loads only when marketing cookie consent is granted and AdSense is live.
 */
export function AdSenseScript() {
  const marketingAllowed = useMarketingConsent();
  const live = isAdSenseLive();
  const clientId = getAdSenseClientId();

  useEffect(() => {
    if (!marketingAllowed || !live || !clientId) {
      document
        .querySelectorAll(`script[${SCRIPT_ATTR}]`)
        .forEach((node) => node.remove());
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
  }, [marketingAllowed, live, clientId]);

  return null;
}
