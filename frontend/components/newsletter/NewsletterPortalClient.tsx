"use client";

import { NewsletterAuthPanel } from "@/components/newsletter/NewsletterAuthPanel";

export function NewsletterPortalClient({
  resubscribe,
  token,
  initialEmail,
}: {
  resubscribe?: boolean;
  token?: string;
  initialEmail?: string;
}) {
  return (
    <NewsletterAuthPanel
      portalLayout
      initialView={resubscribe ? "resubscribe" : "signup"}
      initialEmail={initialEmail}
      initialToken={token}
    />
  );
}
