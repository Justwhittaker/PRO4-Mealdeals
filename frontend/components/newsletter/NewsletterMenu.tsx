"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { Mail } from "lucide-react";
import { NewsletterSignupForm } from "@/components/newsletter/NewsletterSignupForm";
import {
  clearNewsletterSubscribedFlag,
  getRememberedNewsletterEmail,
} from "@/lib/newsletter-storage";
import { getNewsletterStatus } from "@/lib/api";

export function NewsletterMenu() {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"subscribe" | "resubscribe">("subscribe");
  const [email, setEmail] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;

    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const remembered = getRememberedNewsletterEmail();
    if (!remembered) {
      setMode("subscribe");
      setEmail("");
      return;
    }
    setEmail(remembered);
    void getNewsletterStatus(remembered).then((result) => {
      if (result.ok && result.data.exists && !result.data.is_subscribed) {
        clearNewsletterSubscribedFlag();
        setMode("resubscribe");
      } else if (result.ok && result.data.is_subscribed) {
        setMode("resubscribe");
      } else {
        setMode("subscribe");
      }
    });
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        className="rounded-md p-2 text-charcoal-200 transition hover:bg-burgundy-50 hover:text-burgundy-600"
        aria-label="Weekly specials newsletter"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
      >
        <Mail className="h-5 w-5 sm:h-6 sm:w-6" />
      </button>

      {open ? (
        <div
          id={menuId}
          role="menu"
          aria-label="Newsletter"
          className="absolute right-0 z-30 mt-2 w-72 overflow-hidden rounded-md border border-charcoal-700 bg-white p-3 shadow-deal"
        >
          <p className="border-b border-charcoal-800 pb-2 text-[10px] font-medium uppercase tracking-wider text-charcoal-400">
            Weekly Hot Deals
          </p>
          <p className="mt-2 text-xs text-charcoal-300">
            {mode === "resubscribe"
              ? "Already unsubscribed? Subscribe again for Weekly Hot Deals."
              : "Sign up for our Weekly Hot Deals newsletter"}
          </p>
          <div className="mt-3">
            <NewsletterSignupForm
              mode={mode}
              initialEmail={email}
              compact
              submitLabel={
                mode === "resubscribe" ? "Subscribe again" : "Subscribe"
              }
              onSuccess={() => setOpen(false)}
            />
          </div>
          <Link
            href="/newsletter"
            role="menuitem"
            className="mt-3 block text-center text-xs text-burgundy-500 underline-offset-2 hover:underline"
            onClick={() => setOpen(false)}
          >
            Newsletter portal
          </Link>
        </div>
      ) : null}
    </div>
  );
}
