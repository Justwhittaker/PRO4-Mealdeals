"use client";

import { NewsletterAuthIntro } from "@/components/newsletter/NewsletterAuthIntro";
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
    <>
      <NewsletterAuthIntro as="h1" />
      <div className="mt-6">
        <NewsletterAuthPanel
          initialView={resubscribe ? "resubscribe" : "signup"}
          initialEmail={initialEmail}
          initialToken={token}
        />
      </div>
    </>
  );
}
