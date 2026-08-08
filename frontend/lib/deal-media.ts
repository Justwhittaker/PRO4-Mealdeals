/** Shared deal media helpers — keep hero areas filled when scrape URLs fail. */

/** Local last-resort hero when remote deal photos are missing or broken. */
export const DEAL_IMAGE_FALLBACK = "/hero-food.jpg";

/** Drop tracking pixels / junk media; keep http(s) photos and uploaded data URLs. */
export function cleanMediaUrl(value?: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;

  // Merchant deal form stores dropped PNG/JPG/WebP as data URLs in image_url.
  if (/^data:image\/(png|jpe?g|webp|gif);base64,/i.test(trimmed)) {
    return trimmed;
  }

  if (!/^https?:\/\//i.test(trimmed)) return null;
  const lower = trimmed.toLowerCase();
  if (
    /(sprite|pixel|1x1|tracking|spacer|blank\.gif|placeholder\.(png|jpe?g|gif|svg|webp)|\/placeholders?\/|via\.placeholder)/i.test(
      lower,
    )
  ) {
    return null;
  }
  return trimmed;
}

/** Strip legacy scrape boilerplate from user-facing deal copy. */
export function cleanDealDescription(
  value?: string | null,
): string | undefined {
  if (!value) return undefined;
  let text = value
    .replace(/\s*External scraped listing\.?/gi, " ")
    .replace(/\s*Scraped external deal\s*[—-]?\s*/gi, " ")
    .replace(/\s*External listing\s*[—-]?\s*/gi, " ")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+([.!?])/g, "$1")
    .replace(/([.!?])([A-Za-z])/g, "$1 $2")
    .replace(/^[—\-]\s*/, "")
    .trim();
  return text || undefined;
}
