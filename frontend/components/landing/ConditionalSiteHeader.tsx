"use client";

import { usePathname } from "next/navigation";
import { SiteHeader } from "@/components/landing/SiteHeader";

/** Public chrome — hidden on merchant dashboard (has its own shell). */
export function ConditionalSiteHeader() {
  const pathname = usePathname();
  if (pathname?.startsWith("/dashboard")) {
    return null;
  }
  return <SiteHeader />;
}
