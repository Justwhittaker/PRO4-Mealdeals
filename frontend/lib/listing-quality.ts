/**
 * Public listing quality for AdSense review and readers.
 * Mirrors backend/app/services/listing_quality.py.
 */

import { resolveVenueCategory } from "@/lib/categories";

const POLICY_RE =
  /pragmatic\s*play|\bpg\s*soft\b|akun\s*demo|bandar\s+game|slot\s+gratis|game\s+online\s+resmi|terbukti\s+membayar|online\s+casino|\bsportsbook\b|\bporn\b|\bxxx\b|\bviagra\b|\bcialis\b|\bmega\d{2,}\b/i;

const CHROME_RE =
  /\bhome\s*page\b|\bofficial\s+(?:site|website)\b|investor\s+relations|\bnasdaq\b|\bmaintenance\b|store\s+locator|order\s+(?:pizza\s+)?online|\bfind\s+a\s+store\b|\bcoming\s+soon\b|pizza\s+delivery\s+ireland/i;

const OFFER_RE =
  /meal\s+deal|\blunch\b|breakfast\s+bundle|happy\s+hour|drink\s+special|\bbogo\b|buy\s+one|\d+\s*%\s*off|\boffers?\b|\bspecials?\b|\bpromo|early[- ]bird|set\s+menu|spend\s*(?:&|and)\s*save|shop\s+discount|takeaway\s+deal|half[- ]price|hot\s+meal|\bbundle\b|\bdeals?\b/i;

const COMPARISON_RE =
  /\d+\s*%\s*off|\bwas\s+[$£€]?\s?\d|\bhalf[- ]price\b|\bsave\s+[$£€]?\s?\d/i;

export function isPolicyViolation(...parts: Array<string | null | undefined>): boolean {
  const blob = parts.filter(Boolean).join(" ");
  if (!blob.trim()) return false;
  return POLICY_RE.test(blob);
}

export function isLowValueTitle(
  title: string | null | undefined,
  merchant: string,
): boolean {
  const text = (title ?? "").trim();
  if (!text) return true;
  if (CHROME_RE.test(text)) return true;
  if (OFFER_RE.test(text)) return false;
  if (text.includes(":")) return true;
  return norm(text) === norm(merchant) && norm(merchant).length > 0;
}

function publisherListing(
  merchant: string,
  city: string | null | undefined,
  category: string | null | undefined,
): { title: string; description: string } {
  const categoryId = resolveVenueCategory(category, merchant);
  const place = (city ?? "").trim() || "your area";
  const name = merchant.trim() || "This venue";
  switch (categoryId) {
    case "restaurants-cafes-bistros":
      return {
        title: `${name} Lunch Meal Deal — ${place}`,
        description: `Lunch offer at ${name} in ${place}: a set meal, early-bird, or weekday special. Confirm today's price and what is included with the venue before you visit.`,
      };
    case "food-trucks-takeaways":
      return {
        title: `${name} Takeaway Deal — ${place}`,
        description: `Takeaway offer at ${name} in ${place}, such as a meal deal or limited-time menu promotion. Confirm the current offer with the store before you order.`,
      };
    case "wine-farms-entertainment":
      return {
        title: `${name} Tasting & Dining Offer — ${place}`,
        description: `Tasting or dining offer at ${name} in ${place}. Hours and inclusions change, so confirm the current promotion with the venue.`,
      };
    case "delis-grocers":
      return {
        title: `${name} Spend & Save — ${place}`,
        description: `Grocery offer at ${name} in ${place}, such as money off a shop when you spend a set amount. Confirm the current threshold on the store's offers page.`,
      };
    case "clubs-bars-pubs":
      return {
        title: `${name} Happy Hour — ${place}`,
        description: `Drink special at ${name} in ${place}. Happy-hour times and included drinks change, so confirm them with the venue before you go.`,
      };
    case "hotels-resorts-bbs":
      return {
        title: `${name} Hotel Dining Offer — ${place}`,
        description: `Hotel dining offer at ${name} in ${place}, such as a breakfast package or dinner menu. Confirm today's inclusions with the hotel before you book.`,
      };
    default: {
      const unreachable: never = categoryId;
      throw new Error(`Unhandled venue category ${String(unreachable)}`);
    }
  }
}

function publicOriginalPrice(
  dealPrice: number,
  originalPrice: number,
  text: string,
  trust: boolean,
): number {
  if (trust) return originalPrice;
  if (dealPrice <= 0 || originalPrice <= dealPrice) {
    return dealPrice > 0 ? dealPrice : originalPrice;
  }
  const savings = (originalPrice - dealPrice) / originalPrice;
  if (COMPARISON_RE.test(text) && savings >= 0.05 && savings <= 0.55) {
    return originalPrice;
  }
  return dealPrice;
}

export interface PreparedListing {
  blocked: boolean;
  title: string;
  description?: string;
  about: string | null;
  price: number;
  originalPrice: number | null;
  savingsPercent?: number;
}

export function preparePublicListing(input: {
  title?: string | null;
  description?: string | null;
  about?: string | null;
  merchant: string;
  city?: string | null;
  category?: string | null;
  isSubscriber: boolean;
  price: number;
  original: number;
}): PreparedListing {
  const { merchant, isSubscriber } = input;
  if (isPolicyViolation(input.title, input.description, merchant)) {
    return {
      blocked: true,
      title: input.title?.trim() || merchant,
      description: undefined,
      about: null,
      price: 0,
      originalPrice: null,
    };
  }

  const about =
    input.about && !isPolicyViolation(input.about) ? input.about : null;

  let title = (input.title ?? "").trim() || merchant;
  let description = input.description?.trim() || undefined;
  if (!isSubscriber && isLowValueTitle(input.title, merchant)) {
    const copy = publisherListing(merchant, input.city, input.category);
    title = copy.title;
    description = copy.description;
  } else if (!isSubscriber && description && CHROME_RE.test(description)) {
    description = publisherListing(merchant, input.city, input.category).description;
  }

  const price = input.price > 0 ? input.price : 0;
  const shownOriginal = publicOriginalPrice(
    price,
    input.original,
    `${title} ${description ?? ""}`,
    isSubscriber,
  );
  const originalPrice =
    price > 0 && shownOriginal > price ? shownOriginal : null;
  const savingsPercent =
    originalPrice != null
      ? Math.round(((originalPrice - price) / originalPrice) * 100)
      : undefined;

  return {
    blocked: false,
    title,
    description,
    about,
    price,
    originalPrice,
    savingsPercent:
      savingsPercent != null && savingsPercent > 0 ? savingsPercent : undefined,
  };
}

function norm(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}
