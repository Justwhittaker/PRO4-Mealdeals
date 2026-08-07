"use client";

import { useEffect, useState } from "react";
import { NewsletterSignInForm } from "@/components/newsletter/NewsletterSignInForm";
import { NewsletterSignupForm } from "@/components/newsletter/NewsletterSignupForm";
import {
  clearNewsletterSubscribedFlag,
  getRememberedNewsletterEmail,
  isNewsletterSubscribedLocally,
} from "@/lib/newsletter-storage";
import { getNewsletterStatus } from "@/lib/api";

export type NewsletterAuthView = "signup" | "signin" | "resubscribe";

interface NewsletterAuthPanelProps {
  compact?: boolean;
  initialView?: NewsletterAuthView;
  initialEmail?: string;
  initialToken?: string;
  onSuccess?: (email: string) => void;
  signupSubmitLabel?: string;
}

export function NewsletterAuthPanel({
  compact = false,
  initialView = "signup",
  initialEmail = "",
  initialToken,
  onSuccess,
  signupSubmitLabel,
}: NewsletterAuthPanelProps) {
  const [view, setView] = useState<NewsletterAuthView>(initialView);
  const [email, setEmail] = useState(initialEmail);
  const [signedInLocally, setSignedInLocally] = useState(false);

  useEffect(() => {
    setView(initialView);
  }, [initialView]);

  useEffect(() => {
    if (initialEmail) setEmail(initialEmail);
  }, [initialEmail]);

  useEffect(() => {
    const remembered = getRememberedNewsletterEmail();
    if (isNewsletterSubscribedLocally() && remembered) {
      setSignedInLocally(true);
      setEmail(remembered);
      return;
    }
    if (!remembered || initialView === "resubscribe") return;
    setEmail(remembered);
    void getNewsletterStatus(remembered).then((result) => {
      if (result.ok && result.data.exists && !result.data.is_subscribed) {
        clearNewsletterSubscribedFlag();
        setView("resubscribe");
      } else if (result.ok && result.data.is_subscribed) {
        setView("signin");
      }
    });
  }, [initialView]);

  if (signedInLocally) {
    return (
      <div className="space-y-2 text-sm text-charcoal-200">
        <p>
          Signed in as{" "}
          <span className="font-medium text-charcoal-50">{email}</span>
        </p>
        <p className="text-xs text-charcoal-400">
          Deals stay unlocked on this device. On a new phone or after clearing
          cache, use Sign in with the same email.
        </p>
        <button
          type="button"
          className="text-xs text-burgundy-500 underline-offset-2 hover:underline"
          onClick={() => {
            setSignedInLocally(false);
            setView("signin");
          }}
        >
          Use a different email
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {view !== "resubscribe" ? (
        <div
          className="grid grid-cols-2 gap-1 rounded-md border border-charcoal-700 bg-charcoal-950 p-1"
          role="tablist"
          aria-label="Newsletter access"
        >
          <button
            type="button"
            role="tab"
            aria-selected={view === "signup"}
            className={`rounded px-2 py-1.5 text-xs font-medium transition ${
              view === "signup"
                ? "bg-white text-charcoal-50 shadow-sm"
                : "text-charcoal-400 hover:text-charcoal-100"
            }`}
            onClick={() => setView("signup")}
          >
            Sign up
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={view === "signin"}
            className={`rounded px-2 py-1.5 text-xs font-medium transition ${
              view === "signin"
                ? "bg-white text-charcoal-50 shadow-sm"
                : "text-charcoal-400 hover:text-charcoal-100"
            }`}
            onClick={() => setView("signin")}
          >
            Sign in
          </button>
        </div>
      ) : null}

      {view === "signup" ? (
        <>
          <p className="text-xs text-charcoal-300">
            New here? Join Weekly Hot Deals to unlock listings on this device.
          </p>
          <NewsletterSignupForm
            mode="subscribe"
            initialEmail={email}
            compact={compact}
            submitLabel={signupSubmitLabel ?? "Get Weekly Hot Deals"}
            onSuccess={(value) => {
              setEmail(value);
              onSuccess?.(value);
            }}
          />
          <p className="text-center text-xs text-charcoal-400">
            Already subscribed?{" "}
            <button
              type="button"
              className="text-burgundy-500 underline-offset-2 hover:underline"
              onClick={() => setView("signin")}
            >
              Sign in
            </button>
          </p>
        </>
      ) : null}

      {view === "signin" ? (
        <>
          <p className="text-xs text-charcoal-300">
            Returning reader? Enter the email you used for the newsletter —
            we&apos;ll restore deal access on this device.
          </p>
          <NewsletterSignInForm
            compact={compact}
            initialEmail={email}
            onSuccess={(value) => {
              setEmail(value);
              setSignedInLocally(true);
              onSuccess?.(value);
            }}
            onNeedSignup={() => setView("signup")}
            onNeedResubscribe={(value) => {
              setEmail(value);
              setView("resubscribe");
            }}
          />
        </>
      ) : null}

      {view === "resubscribe" ? (
        <>
          <p className="text-xs text-charcoal-300">
            Subscribe again with your email to unlock Weekly Hot Deals.
          </p>
          <NewsletterSignupForm
            mode="resubscribe"
            initialEmail={email}
            initialToken={initialToken}
            compact={compact}
            submitLabel="Subscribe again"
            onSuccess={(value) => {
              setEmail(value);
              onSuccess?.(value);
            }}
          />
          <p className="text-center text-xs text-charcoal-400">
            <button
              type="button"
              className="text-burgundy-500 underline-offset-2 hover:underline"
              onClick={() => setView("signin")}
            >
              Back to sign in
            </button>
          </p>
        </>
      ) : null}
    </div>
  );
}
