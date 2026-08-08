"use client";

import { AdPlaceholder } from "@/components/ads/AdPlaceholder";
import { AdUnit } from "@/components/ads/AdUnit";
import { useMarketingConsent } from "@/components/cookie/CookieConsentProvider";
import {
  getAdSenseClientId,
  getAdSenseInFeedSlotId,
  isAdSenseLive,
} from "@/lib/adsense";

const LAYOUT_KEY =
  process.env.NEXT_PUBLIC_ADSENSE_INFEED_LAYOUT_KEY?.trim() ||
  "-fb+5w+4e-db+86";

export function InFeedAd() {
  const marketingAllowed = useMarketingConsent();
  const live = isAdSenseLive();
  const clientId = getAdSenseClientId();
  const slotId = getAdSenseInFeedSlotId();
  const showAd = marketingAllowed && live && clientId && slotId;

  return (
    <aside
      className="my-2 overflow-hidden rounded-xl border border-charcoal-700/60 bg-charcoal-900/40"
      aria-label="Sponsored"
    >
      {showAd ? (
        <div className="min-h-[120px] px-4 py-6">
          <AdUnit>
            <ins
              className="adsbygoogle"
              style={{ display: "block", width: "100%", minHeight: 100 }}
              data-ad-format="fluid"
              data-ad-layout-key={LAYOUT_KEY}
              data-ad-client={clientId}
              data-ad-slot={slotId}
            />
          </AdUnit>
        </div>
      ) : (
        <AdPlaceholder
          label="Ad space"
          hint={
            marketingAllowed
              ? "Ads unlock on the live site URL"
              : "Enable marketing cookies in Cookie settings to show ads"
          }
          minHeight={120}
        />
      )}
    </aside>
  );
}
