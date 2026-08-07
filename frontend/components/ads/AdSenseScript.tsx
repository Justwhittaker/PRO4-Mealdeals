import { GoogleAdSense } from "next-google-adsense";
import { getAdSensePublisherId, isAdSenseLive } from "@/lib/adsense";

/**
 * Loads AdSense only when the site has a public https URL AdSense can
 * recognise. Until then the script stays off (placeholders still render).
 */
export function AdSenseScript() {
  if (!isAdSenseLive()) return null;
  const publisherId = getAdSensePublisherId();
  if (!publisherId) return null;
  return <GoogleAdSense publisherId={publisherId} isAutoAd={false} />;
}
