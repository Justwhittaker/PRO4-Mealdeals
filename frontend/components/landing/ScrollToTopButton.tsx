"use client";

import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";

/** Fixed bottom-right control — appears after scrolling down so users can jump back to country search. */
export function ScrollToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    function onScroll() {
      setVisible(window.scrollY > 320);
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
      className="fixed bottom-5 right-4 z-[70] flex h-11 w-11 items-center justify-center rounded-md border border-charcoal-700 bg-white text-burgundy-600 shadow-deal transition hover:bg-burgundy-50 sm:bottom-6 sm:right-6"
      aria-label="Scroll to top"
    >
      <ArrowUp className="h-5 w-5" strokeWidth={2.5} />
    </button>
  );
}
