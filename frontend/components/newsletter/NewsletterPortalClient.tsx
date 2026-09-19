"use client";

import { useEffect } from "react";
import { NewsletterAuthPanel } from "@/components/newsletter/NewsletterAuthPanel";
import {
  continuePendingGoRedirect,
  isNewsletterSubscribedLocally,
  isSafeGoNext,
  syncNewsletterUnlockCookie,
} from "@/lib/newsletter-storage";

export function NewsletterPortalClient({
  resubscribe,
  token,
  initialEmail,
  nextPath,
}: {
  resubscribe?: boolean;
  token?: string;
  initialEmail?: string;
  nextPath?: string;
}) {
  useEffect(() => {
    syncNewsletterUnlockCookie();
    if (
      isNewsletterSubscribedLocally() &&
      nextPath &&
      isSafeGoNext(nextPath)
    ) {
      window.location.assign(nextPath);
    }
  }, [nextPath]);

  return (
    <NewsletterAuthPanel
      portalLayout
      initialView={resubscribe ? "resubscribe" : "signup"}
      initialEmail={initialEmail}
      initialToken={token}
      onSuccess={() => {
        continuePendingGoRedirect(nextPath);
      }}
    />
  );
}
