"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  resubscribeNewsletter,
  subscribeNewsletter,
} from "@/lib/api";
import { rememberNewsletterEmail } from "@/lib/newsletter-storage";

type Mode = "subscribe" | "resubscribe";

interface NewsletterSignupFormProps {
  mode?: Mode;
  initialEmail?: string;
  initialToken?: string;
  compact?: boolean;
  onSuccess?: (email: string) => void;
  submitLabel?: string;
}

export function NewsletterSignupForm({
  mode = "subscribe",
  initialEmail = "",
  initialToken,
  compact = false,
  onSuccess,
  submitLabel,
}: NewsletterSignupFormProps) {
  const [name, setName] = useState("");
  const [surname, setSurname] = useState("");
  const [email, setEmail] = useState(initialEmail);
  const [location, setLocation] = useState("");
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!acceptedPrivacy) {
      setError("Please accept the Privacy Notice to continue.");
      return;
    }

    setPending(true);

    if (mode === "resubscribe") {
      const result = await resubscribeNewsletter({
        email: email.trim(),
        token: initialToken,
      });
      setPending(false);
      if (!result.ok) {
        setError(result.error);
        return;
      }
      rememberNewsletterEmail(email.trim());
      setDone(true);
      onSuccess?.(email.trim());
      return;
    }

    const result = await subscribeNewsletter({
      name: name.trim(),
      surname: surname.trim(),
      email: email.trim(),
      location: location.trim(),
    });
    setPending(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    rememberNewsletterEmail(email.trim());
    setDone(true);
    onSuccess?.(email.trim());
  }

  if (done) {
    return (
      <p className="text-sm text-charcoal-100">
        You&apos;re in — Weekly Hot Deals are on the way.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className={compact ? "space-y-3" : "space-y-4"}>
      {mode === "subscribe" ? (
        <>
          <div className={compact ? "grid gap-3" : "grid gap-4 sm:grid-cols-2"}>
            <div className="space-y-1.5">
              <Label htmlFor="nl-name">First name</Label>
              <Input
                id="nl-name"
                name="name"
                autoComplete="given-name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Alex"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="nl-surname">Surname</Label>
              <Input
                id="nl-surname"
                name="surname"
                autoComplete="family-name"
                required
                value={surname}
                onChange={(e) => setSurname(e.target.value)}
                placeholder="Smith"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="nl-email">Email</Label>
            <Input
              id="nl-email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="nl-location">Location</Label>
            <Input
              id="nl-location"
              name="location"
              autoComplete="address-level2"
              required
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="London, UK"
            />
          </div>
        </>
      ) : (
        <div className="space-y-1.5">
          <Label htmlFor="nl-re-email">Email</Label>
          <Input
            id="nl-re-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </div>
      )}

      <div className="flex items-start gap-2.5">
        <input
          id="nl-privacy"
          name="privacy_accepted"
          type="checkbox"
          required
          checked={acceptedPrivacy}
          onChange={(e) => setAcceptedPrivacy(e.target.checked)}
          className="mt-1 h-4 w-4 shrink-0 rounded border-charcoal-600 text-burgundy-600 focus:ring-burgundy-500/40"
        />
        <Label
          htmlFor="nl-privacy"
          className="text-xs font-normal leading-snug text-charcoal-300"
        >
          I have read and accept the{" "}
          <Link
            href="/privacy"
            target="_blank"
            rel="noopener noreferrer"
            className="text-burgundy-600 underline-offset-2 hover:underline"
          >
            Privacy Notice
          </Link>
          , including third-party marketing and compensated data sharing where I
          choose to participate.{" "}
          <Link
            href="/privacy/choices"
            target="_blank"
            rel="noopener noreferrer"
            className="text-burgundy-600 underline-offset-2 hover:underline"
          >
            Privacy Choices
          </Link>
        </Label>
      </div>

      {error ? (
        <p className="text-sm text-burgundy-600" role="alert">
          {error}
        </p>
      ) : null}

      <Button
        type="submit"
        disabled={pending || !acceptedPrivacy}
        className="w-full"
      >
        {pending
          ? "Saving…"
          : submitLabel ??
            (mode === "resubscribe"
              ? "Subscribe again"
              : "Get Weekly Hot Deals")}
      </Button>
    </form>
  );
}
