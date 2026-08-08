"use client";

import { AdUnit } from "next-google-adsense";
import { AdPlaceholder } from "@/components/ads/AdPlaceholder";
import { useMarketingConsent } from "@/components/cookie/CookieConsentProvider";
import {
  getAdSensePublisherId,
  getAdSenseSidebarSlotId,
  isAdSenseLive,
} from "@/lib/adsense";

export function SidebarAd() {
  const marketingAllowed = useMarketingConsent();
  const live = isAdSenseLive();
  const publisherId = getAdSensePublisherId();
  const slotId = getAdSenseSidebarSlotId();
  const showAd = marketingAllowed && live && publisherId && slotId;

  return (
    <aside
      className="sticky top-24 overflow-hidden rounded-xl border border-charcoal-700/60 bg-charcoal-900/50"
      aria-label="Sponsored sidebar"
    >
      <div className="flex min-h-[250px] w-full items-center justify-center p-4">
        {showAd ? (
          <AdUnit
            publisherId={publisherId}
            slotId={slotId}
            layout="display"
            dummySize="MEDIUM_RECTANGLE"
          />
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
