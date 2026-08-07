/** Public product brand — keep UI strings in sync with dineadeal.com */

export const BRAND_NAME = "Dine A Deal";
export const BRAND_NAME_COMPACT = "DineADeal";
export const BRAND_DOMAIN = "dineadeal.com";
export const BRAND_LOGO_SRC = "/logo-dineadeal.png";
export const BRAND_WORDMARK_SRC = "/logo-wordmark.png";
export const BRAND_SITE_URL =
  process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "") ||
  `https://${BRAND_DOMAIN}`;
export const BRAND_CONTACT_EMAIL =
  process.env.NEXT_PUBLIC_CONTACT_EMAIL?.trim() || `hello@${BRAND_DOMAIN}`;
export const BRAND_TAGLINE = "Local lunch deals, worldwide";
