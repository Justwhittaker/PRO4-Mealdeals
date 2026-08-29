"use client";

import { AdUnit } from "@/components/ads/AdUnit";
import { useMarketingConsent } from "@/components/cookie/CookieConsentProvider";
import {
  getAdSenseClientId,
  getAdSenseSidebarSlotId,
  isAdSenseLive,
} from "@/lib/adsense";

/** Sidebar unit beside deal lists. Renders nothing unless a live slot can fill. */
export function SidebarAd() {
  const marketingAllowed = useMarketingConsent();
  const live = isAdSenseLive();
  const clientId = getAdSenseClientId();
  const slotId = getAdSenseSidebarSlotId();
  const showAd = marketingAllowed && live && clientId && slotId;

  if (!showAd) return null;

  return (
    <aside
      className="sticky top-24 overflow-hidden rounded-xl border border-charcoal-700/60 bg-charcoal-900/50"
      aria-label="Sponsored sidebar"
    >
      <div className="flex min-h-[250px] w-full items-center justify-center p-4">
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
      </div>
    </aside>
  );
}
