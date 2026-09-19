"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import {
  NEWSLETTER_ACCESS_EVENT,
  isNewsletterSubscribedLocally,
  syncNewsletterUnlockCookie,
} from "@/lib/newsletter-storage";

function subscribeNewsletterAccess(onStoreChange: () => void): () => void {
  window.addEventListener(NEWSLETTER_ACCESS_EVENT, onStoreChange);
  window.addEventListener("storage", onStoreChange);
  return () => {
    window.removeEventListener(NEWSLETTER_ACCESS_EVENT, onStoreChange);
    window.removeEventListener("storage", onStoreChange);
  };
}

function getNewsletterAccessSnapshot(): boolean {
  return isNewsletterSubscribedLocally();
}

function getNewsletterAccessServerSnapshot(): boolean {
  return false;
}

/** True after this device has signed up / signed in for the newsletter. */
export function useNewsletterAccess(): { ready: boolean; unlocked: boolean } {
  const [ready, setReady] = useState(false);
  const unlocked = useSyncExternalStore(
    subscribeNewsletterAccess,
    getNewsletterAccessSnapshot,
    getNewsletterAccessServerSnapshot,
  );

  useEffect(() => {
    syncNewsletterUnlockCookie();
    setReady(true);
  }, []);

  return { ready, unlocked };
}
