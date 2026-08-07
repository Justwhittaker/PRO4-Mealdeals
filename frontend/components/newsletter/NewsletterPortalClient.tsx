"use client";

import { NewsletterSignupForm } from "@/components/newsletter/NewsletterSignupForm";

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
    <NewsletterSignupForm
      mode={resubscribe ? "resubscribe" : "subscribe"}
      initialEmail={initialEmail}
      initialToken={token}
      submitLabel={
        resubscribe ? "Subscribe again" : "Join Friday weekly specials"
      }
    />
  );
}
