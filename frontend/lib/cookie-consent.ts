/** First-party cookie consent — necessary always on; analytics/marketing opt-in. */

export const CONSENT_STORAGE_KEY = "cookie_consent";
export const CONSENT_COOKIE_NAME = "cookie_consent";
export const CONSENT_UPDATED_EVENT = "cookie-consent-updated";
export const CONSENT_OPEN_SETTINGS_EVENT = "cookie-consent-open-settings";

export type ConsentState = {
  necessary: true;
  analytics: boolean;
  marketing: boolean;
  updatedAt: string;
};

const DEFAULT_CONSENT: ConsentState = {
  necessary: true,
  analytics: false,
  marketing: false,
  updatedAt: "",
};

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function parseConsent(raw: string | null | undefined): ConsentState | null {
  if (!raw) return null;
  try {
    const data = JSON.parse(raw) as Partial<ConsentState>;
    if (typeof data !== "object" || data === null) return null;
    return {
      necessary: true,
      analytics: Boolean(data.analytics),
      marketing: Boolean(data.marketing),
      updatedAt:
        typeof data.updatedAt === "string" && data.updatedAt
          ? data.updatedAt
          : new Date().toISOString(),
    };
  } catch {
    return null;
  }
}

function writeCookie(value: string): void {
  if (!isBrowser()) return;
  const maxAge = 60 * 60 * 24 * 365;
  document.cookie = `${CONSENT_COOKIE_NAME}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAge}; SameSite=Lax`;
}

function readCookie(): string | null {
  if (!isBrowser()) return null;
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${CONSENT_COOKIE_NAME}=`));
  if (!match) return null;
  return decodeURIComponent(match.slice(CONSENT_COOKIE_NAME.length + 1));
}

export function getConsent(): ConsentState {
  if (!isBrowser()) return { ...DEFAULT_CONSENT };
  const fromStorage = parseConsent(localStorage.getItem(CONSENT_STORAGE_KEY));
  if (fromStorage) return fromStorage;
  const fromCookie = parseConsent(readCookie());
  if (fromCookie) return fromCookie;
  return { ...DEFAULT_CONSENT };
}

export function hasAnswered(): boolean {
  if (!isBrowser()) return false;
  if (localStorage.getItem(CONSENT_STORAGE_KEY)) return true;
  return Boolean(readCookie());
}

export function setConsent(
  partial: Partial<Pick<ConsentState, "analytics" | "marketing">>,
): ConsentState {
  const next: ConsentState = {
    necessary: true,
    analytics: Boolean(partial.analytics),
    marketing: Boolean(partial.marketing),
    updatedAt: new Date().toISOString(),
  };
  if (!isBrowser()) return next;
  const raw = JSON.stringify(next);
  localStorage.setItem(CONSENT_STORAGE_KEY, raw);
  writeCookie(raw);
  window.dispatchEvent(
    new CustomEvent(CONSENT_UPDATED_EVENT, { detail: next }),
  );
  return next;
}

export function acceptAll(): ConsentState {
  return setConsent({ analytics: true, marketing: true });
}

export function rejectNonEssential(): ConsentState {
  return setConsent({ analytics: false, marketing: false });
}

export function canUseAnalytics(consent = getConsent()): boolean {
  return consent.analytics === true;
}

export function canUseMarketing(consent = getConsent()): boolean {
  return consent.marketing === true;
}

export function openCookieSettings(): void {
  if (!isBrowser()) return;
  window.dispatchEvent(new Event(CONSENT_OPEN_SETTINGS_EVENT));
}
