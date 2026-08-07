"use client";

import { AdUnit } from "next-google-adsense";
import { AdPlaceholder } from "@/components/ads/AdPlaceholder";
import {
  getAdSenseInFeedSlotId,
  getAdSensePublisherId,
  isAdSenseLive,
} from "@/lib/adsense";

const LAYOUT_KEY =
  process.env.NEXT_PUBLIC_ADSENSE_INFEED_LAYOUT_KEY?.trim() ||
  "-fb+5w+4e-db+86";

function InFeedIns({
  clientId,
  slotId,
}: {
  clientId: string;
  slotId: string;
}) {
  return (
    <ins
      className="adsbygoogle"
      style={{ display: "block", width: "100%", minHeight: 100 }}
      data-ad-format="fluid"
      data-ad-layout-key={LAYOUT_KEY}
      data-ad-client={clientId}
      data-ad-slot={slotId}
    />
  );
}

export function InFeedAd() {
  const live = isAdSenseLive();
  const publisherId = getAdSensePublisherId();
  const slotId = getAdSenseInFeedSlotId();

  return (
    <aside
      className="my-2 overflow-hidden rounded-xl border border-charcoal-700/60 bg-charcoal-900/40"
      aria-label="Sponsored"
    >
      {live && publisherId && slotId ? (
        <div className="min-h-[120px] px-4 py-6">
          <AdUnit
            publisherId={publisherId}
            slotId={slotId}
            layout="custom"
            customLayout={
              <InFeedIns
                clientId={
                  publisherId.startsWith("ca-")
                    ? publisherId
                    : `ca-${publisherId}`
                }
                slotId={slotId}
              />
            }
          />
        </div>
      ) : (
        <AdPlaceholder label="Ad space" minHeight={120} />
      )}
    </aside>
  );
}
