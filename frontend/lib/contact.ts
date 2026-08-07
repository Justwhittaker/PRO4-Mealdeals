import { BRAND_NAME_COMPACT } from "@/lib/brand";

/** Public contact mailbox (override with NEXT_PUBLIC_CONTACT_EMAIL). */
export const CONTACT_EMAIL = "just.whittaker@gmail.com";

export function contactMailto(
  subject = `${BRAND_NAME_COMPACT} enquiry`,
): string {
  return `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}`;
}
