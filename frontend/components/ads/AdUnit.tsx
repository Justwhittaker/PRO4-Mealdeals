"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { usePathname } from "next/navigation";

declare global {
  interface Window {
    adsbygoogle?: unknown[];
  }
}

/**
 * Wraps an AdSense <ins> and pushes it into adsbygoogle after mount / route change.
 * No next-google-adsense / next/script dependency.
 */
export function AdUnit({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current?.offsetWidth) return;
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch {
      // AdSense may throw if the unit was already filled.
    }
  }, [pathname]);

  return <div ref={containerRef}>{children}</div>;
}
