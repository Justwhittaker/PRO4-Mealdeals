/**
 * Google AdSense helpers.
 *
 * AdSense will not approve or serve on localhost / preview URLs.
 * Keep slots in the UI as reserved placeholders until
 * `NEXT_PUBLIC_APP_URL` is a public https origin and publisher IDs are set.
 */

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

export function getAdSensePublisherId(): string | undefined {
  const publisher = process.env.NEXT_PUBLIC_ADSENSE_PUBLISHER_ID?.trim();
  if (publisher) {
    return publisher.replace(/^ca-/, "");
  }
  const client = process.env.NEXT_PUBLIC_ADSENSE_CLIENT?.trim();
  if (!client) return undefined;
  return client.replace(/^ca-/, "");
}

export function getAdSenseInFeedSlotId(): string | undefined {
  return process.env.NEXT_PUBLIC_ADSENSE_SLOT_INFEED?.trim() || undefined;
}

export function getAdSenseSidebarSlotId(): string | undefined {
  return process.env.NEXT_PUBLIC_ADSENSE_SLOT_SIDEBAR?.trim() || undefined;
}

/** True when publisher id looks configured (not a placeholder). */
export function isAdSenseConfigured(): boolean {
  const id = getAdSensePublisherId();
  if (!id) return false;
  if (/x{4,}/i.test(id)) return false;
  return /^pub-\d{16}$/.test(id);
}

/**
 * AdSense site verification requires a real public URL.
 * localhost, *.vercel.app preview, and http origins stay off.
 */
export function isAdSenseEligibleAppUrl(
  appUrl = process.env.NEXT_PUBLIC_APP_URL,
): boolean {
  if (!appUrl?.trim()) return false;
  try {
    const url = new URL(appUrl.trim());
    if (url.protocol !== "https:") return false;
    if (LOCAL_HOSTS.has(url.hostname)) return false;
    if (url.hostname.endsWith(".local")) return false;
    // Optional: allow production custom domains only (skip Vercel previews)
    if (
      process.env.NEXT_PUBLIC_ADSENSE_ALLOW_VERCEL_PREVIEW !== "true" &&
      url.hostname.endsWith(".vercel.app")
    ) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

/** True when at least one manual ad unit slot is configured. */
export function hasAdSenseSlots(): boolean {
  return Boolean(getAdSenseInFeedSlotId() || getAdSenseSidebarSlotId());
}

/**
 * Auto ads place units on every screen, including forms, gates, and overlays.
 * Keep this off — only manual in-feed / sidebar slots next to deal lists.
 */
export function shouldUseAdSenseAutoAds(): boolean {
  return false;
}

const ADSENSE_RESERVED_ROOTS = new Set([
  "dashboard",
  "contact",
  "newsletter",
  "privacy",
  "cookies",
  "terms",
  "about",
  "go",
  "api",
  "admin",
]);

/**
 * Pages without a deal inventory (forms, legal, auth, marketing).
 * AdSense must not load here — policy: ads on screens without publisher content.
 */
export function isAdSenseBlockedPath(pathname: string | null): boolean {
  return !isAdSenseListingPath(pathname);
}

/**
 * Homepage, country, and city listing pages only.
 * Deal detail, admin, dashboard, and legal/form routes stay ad-free.
 */
export function isAdSenseListingPath(pathname: string | null): boolean {
  if (!pathname) return false;
  const path = pathname.split("?")[0]?.toLowerCase() ?? "";
  const parts = path.split("/").filter(Boolean);
  if (parts.length === 0) return true;
  if (ADSENSE_RESERVED_ROOTS.has(parts[0]!)) return false;
  return parts.length === 1 || parts.length === 2;
}

/**
 * Live AdSense script when:
 * - publisher ID is configured
 * - at least one manual slot ID exists (no Auto ads)
 * - site has a public https URL AdSense can crawl
 * - not forced off via NEXT_PUBLIC_ADSENSE_ENABLED=false
 */
export function isAdSenseLive(): boolean {
  if (process.env.NEXT_PUBLIC_ADSENSE_ENABLED === "false") return false;
  if (!isAdSenseConfigured()) return false;
  if (!hasAdSenseSlots()) return false;
  if (!isAdSenseEligibleAppUrl()) return false;
  // Explicit opt-in once domain is ready (avoids accidental live calls pre-launch)
  if (process.env.NEXT_PUBLIC_ADSENSE_ENABLED === "true") return true;
  // Default: live in production builds only when URL is eligible
  return process.env.NODE_ENV === "production";
}

/** `ca-pub-…` form for meta tags / AdSense client attributes. */
export function getAdSenseClientId(): string | undefined {
  const id = getAdSensePublisherId();
  if (!id) return undefined;
  return id.startsWith("ca-") ? id : `ca-${id}`;
}
