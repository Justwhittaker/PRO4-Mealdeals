"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getNewsletterStatus } from "@/lib/api";
import { rememberNewsletterEmail } from "@/lib/newsletter-storage";

interface NewsletterSignInFormProps {
  compact?: boolean;
  initialEmail?: string;
  onSuccess?: (email: string) => void;
  onNeedSignup?: () => void;
  onNeedResubscribe?: (email: string) => void;
}

export function NewsletterSignInForm({
  compact = false,
  initialEmail = "",
  onSuccess,
  onNeedSignup,
  onNeedResubscribe,
}: NewsletterSignInFormProps) {
  const [email, setEmail] = useState(initialEmail);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);

    const trimmed = email.trim().toLowerCase();
    const result = await getNewsletterStatus(trimmed);
    setPending(false);

    if (!result.ok) {
      setError(result.error);
      return;
    }

    if (!result.data.exists) {
      setError("No newsletter account for that email yet.");
      return;
    }

    if (!result.data.is_subscribed) {
      setError("That email is unsubscribed. Subscribe again to unlock deals.");
      onNeedResubscribe?.(trimmed);
      return;
    }

    rememberNewsletterEmail(trimmed);
    setDone(true);
    onSuccess?.(trimmed);
  }

  if (done) {
    return (
      <p className="text-sm text-charcoal-100">
        Welcome back — your deals access is restored on this device.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className={compact ? "space-y-3" : "space-y-4"}>
      <div className="space-y-1.5">
        <Label htmlFor="nl-signin-email">Email</Label>
        <Input
          id="nl-signin-email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
      </div>

      {error ? (
        <div className="space-y-2" role="alert">
          <p className="text-sm text-burgundy-600">{error}</p>
          {!error.includes("unsubscribed") && onNeedSignup ? (
            <button
              type="button"
              className="text-xs text-burgundy-500 underline-offset-2 hover:underline"
              onClick={onNeedSignup}
            >
              Sign up for the newsletter instead
            </button>
          ) : null}
        </div>
      ) : null}

      <Button type="submit" disabled={pending} className="w-full">
        {pending ? "Checking…" : "Restore access"}
      </Button>
    </form>
  );
}
