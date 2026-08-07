const EMAIL_KEY = "dineadeal_newsletter_email";
const DISMISS_KEY = "dineadeal_newsletter_popup_dismissed";
const SUBSCRIBED_KEY = "dineadeal_newsletter_subscribed";

/** Persist newsletter identity + unlock deals for this browser. */
export function rememberNewsletterEmail(email: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(EMAIL_KEY, email.trim().toLowerCase());
  localStorage.setItem(SUBSCRIBED_KEY, "1");
  localStorage.setItem(DISMISS_KEY, "1");
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

export function clearNewsletterSubscribedFlag(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SUBSCRIBED_KEY);
}

/** Clear local unlock + remembered email (e.g. after unsubscribe). */
export function clearNewsletterSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SUBSCRIBED_KEY);
  localStorage.removeItem(EMAIL_KEY);
}
