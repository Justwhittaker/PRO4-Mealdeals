"use client";

import { AdPlaceholder } from "@/components/ads/AdPlaceholder";
import { AdUnit } from "@/components/ads/AdUnit";
import { useMarketingConsent } from "@/components/cookie/CookieConsentProvider";
import {
  getAdSenseClientId,
  getAdSenseSidebarSlotId,
  isAdSenseLive,
} from "@/lib/adsense";

export function SidebarAd() {
  const marketingAllowed = useMarketingConsent();
  const live = isAdSenseLive();
  const clientId = getAdSenseClientId();
  const slotId = getAdSenseSidebarSlotId();
  const showAd = marketingAllowed && live && clientId && slotId;

  return (
    <aside
      className="sticky top-24 overflow-hidden rounded-xl border border-charcoal-700/60 bg-charcoal-900/50"
      aria-label="Sponsored sidebar"
    >
      <div className="flex min-h-[250px] w-full items-center justify-center p-4">
        {showAd ? (
          <AdUnit>
            <ins
              className="adsbygoogle"
              style={{ display: "block", width: "100%" }}
              data-ad-format="auto"
              data-full-width-responsive="true"
              data-ad-client={clientId}
              data-ad-slot={slotId}
            />
          </AdUnit>
        ) : (
          <AdPlaceholder
            label="Sticky ad"
            hint={
              marketingAllowed
                ? "Ads unlock on the live site URL"
                : "Enable marketing cookies in Cookie settings to show ads"
            }
            minHeight={250}
          />
        )}
      </div>
    </aside>
  );
}
