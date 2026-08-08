"use client";

import { GoogleAdSense } from "next-google-adsense";
import {
  getAdSensePublisherId,
  isAdSenseLive,
  shouldUseAdSenseAutoAds,
} from "@/lib/adsense";
import { useMarketingConsent } from "@/components/cookie/CookieConsentProvider";

/**
 * Loads AdSense only when:
 * - public https URL + publisher configured
 * - marketing cookie consent is granted
 *
 * Auto ads: when publisher is set but slot IDs are not.
 * Manual units: InFeedAd / SidebarAd once slot env vars exist.
 */
export function AdSenseScript() {
  const marketingAllowed = useMarketingConsent();
  if (!marketingAllowed) return null;
  if (!isAdSenseLive()) return null;
  const publisherId = getAdSensePublisherId();
  if (!publisherId) return null;
  return (
    <GoogleAdSense
      publisherId={publisherId}
      isAutoAd={shouldUseAdSenseAutoAds()}
    />
  );
}
