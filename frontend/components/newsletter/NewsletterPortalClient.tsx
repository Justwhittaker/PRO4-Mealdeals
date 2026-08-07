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
      initialView={resubscribe ? "resubscribe" : "signup"}
      initialEmail={initialEmail}
      initialToken={token}
      signupSubmitLabel={
        resubscribe ? "Subscribe again" : "Join Friday weekly specials"
      }
    />
  );
}
