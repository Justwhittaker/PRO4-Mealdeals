const EMAIL_KEY = "dineadeal_newsletter_email";
const DISMISS_KEY = "dineadeal_newsletter_popup_dismissed";
const SUBSCRIBED_KEY = "dineadeal_newsletter_subscribed";
const PENDING_GO_KEY = "dineadeal_pending_go";

/** Readable cookie so /go can enforce newsletter on the server. */
export const NEWSLETTER_UNLOCK_COOKIE = "dineadeal_newsletter_unlock";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

/** Force-open the newsletter popup (e.g. from deal-gate CTA). */
export const NEWSLETTER_OPEN_EVENT = "dineadeal:newsletter-open";
/** Fired when local subscribe unlock changes (signup, sign-in, clear). */
export const NEWSLETTER_ACCESS_EVENT = "dineadeal:newsletter-access";

function notifyNewsletterAccessChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(NEWSLETTER_ACCESS_EVENT));
}

function writeUnlockCookie(enabled: boolean): void {
  if (typeof document === "undefined") return;
  const secure =
    typeof window !== "undefined" && window.location.protocol === "https:"
      ? "; Secure"
      : "";
  if (enabled) {
    document.cookie = `${NEWSLETTER_UNLOCK_COOKIE}=1; Path=/; Max-Age=${COOKIE_MAX_AGE}; SameSite=Lax${secure}`;
    return;
  }
  document.cookie = `${NEWSLETTER_UNLOCK_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax${secure}`;
}

/** Keep the /go cookie in sync with the local unlock flag. */
export function syncNewsletterUnlockCookie(): void {
  writeUnlockCookie(isNewsletterSubscribedLocally());
}

/** Persist newsletter identity + unlock outbound deal CTAs for this browser. */
export function rememberNewsletterEmail(email: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(EMAIL_KEY, email.trim().toLowerCase());
  localStorage.setItem(SUBSCRIBED_KEY, "1");
  localStorage.setItem(DISMISS_KEY, "1");
  writeUnlockCookie(true);
  notifyNewsletterAccessChanged();
}

export function getRememberedNewsletterEmail(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(EMAIL_KEY);
}

/** Local cache unlock — true after signup or sign-in on this device. */
export function isNewsletterSubscribedLocally(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(SUBSCRIBED_KEY) === "1";
}

export function markNewsletterPopupDismissed(): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(DISMISS_KEY, "1");
}

export function shouldShowNewsletterPopup(): boolean {
  if (typeof window === "undefined") return false;
  if (isNewsletterSubscribedLocally()) return false;
  if (localStorage.getItem(DISMISS_KEY) === "1") return false;
  return true;
}

/** Open newsletter signup UI even after a prior dismiss. */
export function openNewsletterSignup(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(NEWSLETTER_OPEN_EVENT));
}

export function clearNewsletterSubscribedFlag(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SUBSCRIBED_KEY);
  writeUnlockCookie(false);
  notifyNewsletterAccessChanged();
}

/** Clear local unlock + remembered email (e.g. after unsubscribe). */
export function clearNewsletterSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SUBSCRIBED_KEY);
  localStorage.removeItem(EMAIL_KEY);
  writeUnlockCookie(false);
  notifyNewsletterAccessChanged();
}

const GO_DEAL_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const GO_PATH =
  /^\/go\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/?$/i;
const UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign"] as const;
const UTM_VALUE = /^[A-Za-z0-9_]{1,64}$/;

export function isGoDealId(value: string): boolean {
  return GO_DEAL_ID.test(value);
}

/** Copy only the weekly-specials referral tags from a page or /go query. */
export function utmQueryString(search: string): string {
  const raw = search.startsWith("?") ? search.slice(1) : search;
  const incoming = new URLSearchParams(raw);
  const utm = new URLSearchParams();
  for (const key of UTM_KEYS) {
    const value = incoming.get(key);
    if (value && UTM_VALUE.test(value)) utm.set(key, value);
  }
  return utm.toString();
}

/** Deal-page "View deal" href. Forwards newsletter UTM into /go so clicks are counted. */
export function trackedGoPath(dealId: string, search?: string): string {
  const source =
    search ?? (typeof window !== "undefined" ? window.location.search : "");
  const query = utmQueryString(source);
  return query ? `/go/${dealId}?${query}` : `/go/${dealId}`;
}

export function isSafeGoNext(path: string): boolean {
  const trimmed = path.trim();
  const splitAt = trimmed.indexOf("?");
  const pathname = splitAt === -1 ? trimmed : trimmed.slice(0, splitAt);
  const query = splitAt === -1 ? "" : trimmed.slice(splitAt + 1);
  if (!GO_PATH.test(pathname)) return false;
  if (!query) return true;
  const params = new URLSearchParams(query);
  const keys = Array.from(params.keys());
  if (keys.length === 0 || keys.length > UTM_KEYS.length) return false;
  const allowed = new Set<string>(UTM_KEYS);
  return keys.every((key) => {
    const value = params.get(key);
    return allowed.has(key) && Boolean(value && UTM_VALUE.test(value));
  });
}

export function setPendingGoDealId(dealId: string): void {
  if (typeof window === "undefined" || !isGoDealId(dealId)) return;
  sessionStorage.setItem(PENDING_GO_KEY, dealId);
}

export function getPendingGoDealId(): string | null {
  if (typeof window === "undefined") return null;
  const value = sessionStorage.getItem(PENDING_GO_KEY);
  return value && isGoDealId(value) ? value : null;
}

export function takePendingGoDealId(): string | null {
  if (typeof window === "undefined") return null;
  const value = sessionStorage.getItem(PENDING_GO_KEY);
  sessionStorage.removeItem(PENDING_GO_KEY);
  return value && isGoDealId(value) ? value : null;
}

/** After signup/sign-in, continue the locked /go click when one is pending. */
export function continuePendingGoRedirect(nextFromQuery?: string | null): void {
  if (typeof window === "undefined") return;
  const pending = takePendingGoDealId();
  if (pending) {
    window.location.assign(trackedGoPath(pending));
    return;
  }
  if (nextFromQuery && isSafeGoNext(nextFromQuery)) {
    window.location.assign(nextFromQuery);
  }
}
