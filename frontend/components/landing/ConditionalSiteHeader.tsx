"use client";

import { usePathname } from "next/navigation";

/** Public chrome — hidden on merchant dashboard (has its own shell). */
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
