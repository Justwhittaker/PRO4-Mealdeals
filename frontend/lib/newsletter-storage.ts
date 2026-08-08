const EMAIL_KEY = "dineadeal_newsletter_email";
const DISMISS_KEY = "dineadeal_newsletter_popup_dismissed";
const SUBSCRIBED_KEY = "dineadeal_newsletter_subscribed";

/** Force-open the newsletter popup (e.g. from deal-gate CTA). */
export const NEWSLETTER_OPEN_EVENT = "dineadeal:newsletter-open";
/** Fired when local subscribe unlock changes (signup, sign-in, clear). */
export const NEWSLETTER_ACCESS_EVENT = "dineadeal:newsletter-access";

function notifyNewsletterAccessChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(NEWSLETTER_ACCESS_EVENT));
}

/** Persist newsletter identity + unlock deals for this browser. */
export function rememberNewsletterEmail(email: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(EMAIL_KEY, email.trim().toLowerCase());
  localStorage.setItem(SUBSCRIBED_KEY, "1");
  localStorage.setItem(DISMISS_KEY, "1");
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
  notifyNewsletterAccessChanged();
}

/** Clear local unlock + remembered email (e.g. after unsubscribe). */
export function clearNewsletterSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SUBSCRIBED_KEY);
  localStorage.removeItem(EMAIL_KEY);
  notifyNewsletterAccessChanged();
}
