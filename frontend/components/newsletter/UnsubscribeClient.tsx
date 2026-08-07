"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { unsubscribeNewsletter } from "@/lib/api";
import { clearNewsletterSubscribedFlag } from "@/lib/newsletter-storage";

export function UnsubscribeClient() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Missing unsubscribe token.");
      return;
    }
    setStatus("loading");
    void unsubscribeNewsletter(token).then((result) => {
      if (!result.ok) {
        setStatus("error");
        setMessage(result.error);
        return;
      }
      clearNewsletterSubscribedFlag();
      setEmail(result.data.email);
      setMessage(result.data.message);
      setStatus("done");
    });
  }, [token]);

  if (status === "loading" || status === "idle") {
    return (
      <p className="mt-4 text-sm text-charcoal-300">Updating preferences…</p>
    );
  }

  if (status === "error") {
    return (
      <p className="mt-4 text-sm text-burgundy-600" role="alert">
        {message}
      </p>
    );
  }

  return (
    <div className="mt-4 space-y-4 text-sm text-charcoal-200">
      <p>{message}</p>
      <p>
        Your details remain on file
        {email ? ` (${email})` : ""}. Use the mail icon next to your profile to
        subscribe again anytime.
      </p>
      <Button asChild>
        <Link
          href={`/newsletter?resubscribe=1${email ? `&email=${encodeURIComponent(email)}` : ""}${token ? `&token=${encodeURIComponent(token)}` : ""}`}
        >
          Subscribe again
        </Link>
      </Button>
    </div>
  );
}
