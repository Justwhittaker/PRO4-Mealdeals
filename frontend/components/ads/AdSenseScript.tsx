import { GoogleAdSense } from "next-google-adsense";
import {
  getAdSensePublisherId,
  isAdSenseLive,
  shouldUseAdSenseAutoAds,
} from "@/lib/adsense";

/**
 * Loads AdSense only when the site has a public https URL AdSense can
 * recognise. Until then the script stays off (placeholders still render).
 *
 * Auto ads: enabled when publisher is set but slot IDs are not (first connect).
 * Manual units: InFeedAd / SidebarAd once slot env vars exist.
 */
export function AdSenseScript() {
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
