"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { ArrowUp } from "lucide-react";

const SCROLL_THRESHOLD_PX = 400;

/**
 * Mobile back-to-top control for public pages.
 * Hidden on dashboard routes and at md+ breakpoints to avoid chrome clutter.
 */
export function ScrollToTopButton() {
  const pathname = usePathname();
  const [visible, setVisible] = useState(false);
  const isDashboard = pathname?.startsWith("/dashboard") ?? false;

  useEffect(() => {
    if (isDashboard) {
      setVisible(false);
      return;
    }

    function onScroll() {
      setVisible(window.scrollY > SCROLL_THRESHOLD_PX);
    }

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [isDashboard]);

  if (isDashboard || !visible) return null;

  return (
    <button
      type="button"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      className="fixed bottom-5 right-4 z-50 flex h-11 w-11 items-center justify-center rounded-md border border-charcoal-700 bg-white text-burgundy-600 shadow-deal transition hover:bg-burgundy-50 md:hidden"
      aria-label="Back to top"
    >
      <ArrowUp className="h-5 w-5" strokeWidth={2.5} aria-hidden />
    </button>
  );
}
