"use client";

import { usePathname } from "next/navigation";

/**
 * Optional public overlays (e.g. newsletter popup).
 * SiteHeader (incl. deal counter) always stays mounted in the root layout.
 */
export function ConditionalSiteHeader({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  if (pathname?.startsWith("/dashboard")) {
    return null;
  }
  return children;
}
