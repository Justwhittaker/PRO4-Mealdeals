"use client";

import { openCookieSettings } from "@/lib/cookie-consent";

export function CookieSettingsLink({
  className = "uppercase tracking-wider transition hover:text-burgundy-500",
}: {
  className?: string;
}) {
  return (
    <button type="button" className={className} onClick={openCookieSettings}>
      Cookie settings
    </button>
  );
}
