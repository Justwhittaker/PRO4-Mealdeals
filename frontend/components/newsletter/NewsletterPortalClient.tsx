"use client";

import { useEffect, useState } from "react";
import { NewsletterAuthIntro } from "@/components/newsletter/NewsletterAuthIntro";
import { NewsletterAuthPanel } from "@/components/newsletter/NewsletterAuthPanel";
import {
  getRememberedNewsletterEmail,
  isNewsletterSubscribedLocally,
} from "@/lib/newsletter-storage";

export function NewsletterPortalClient({
  resubscribe,
  token,
  initialEmail,
}: {
  resubscribe?: boolean;
  token?: string;
  initialEmail?: string;
}) {
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    const remembered = getRememberedNewsletterEmail();
    setSignedIn(Boolean(isNewsletterSubscribedLocally() && remembered));
  }, []);

  return (
    <div className="w-full">
      {/*
        Signed-in: intro lives inside the panel, directly above “Signed in as …”.
        Signed-out: intro stays at the top of the portal box.
      */}
      {!signedIn ? (
        <NewsletterAuthIntro as="h1" className="text-center" />
      ) : null}
      <div className={signedIn ? undefined : "mt-6 text-left"}>
        <NewsletterAuthPanel
          portalLayout
          initialView={resubscribe ? "resubscribe" : "signup"}
          initialEmail={initialEmail}
          initialToken={token}
          onSignedInChange={setSignedIn}
        />
      </div>
    </div>
  );
}
