"use client";

import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";

const SCROLL_THRESHOLD_PX = 360;

/**
 * “Back to top” control for all viewport sizes.
 * Mount under ConditionalSiteHeader so it stays off /dashboard.
 */
export function ScrollToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    function onScroll() {
      setVisible(window.scrollY > SCROLL_THRESHOLD_PX);
    }

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible) return null;

  return (
    <button
      type="button"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      className="fixed right-4 z-50 flex h-11 w-11 items-center justify-center rounded-md border border-charcoal-700 bg-white text-burgundy-600 shadow-deal transition hover:bg-burgundy-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-burgundy-500 focus-visible:ring-offset-2"
      style={{ bottom: "max(1.25rem, env(safe-area-inset-bottom))" }}
      aria-label="Back to top"
    >
      <ArrowUp className="h-5 w-5" strokeWidth={2.5} aria-hidden />
    </button>
  );
}
