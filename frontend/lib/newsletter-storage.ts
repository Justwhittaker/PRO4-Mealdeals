const EMAIL_KEY = "dineadeal_newsletter_email";
const DISMISS_KEY = "dineadeal_newsletter_popup_dismissed";
const SUBSCRIBED_KEY = "dineadeal_newsletter_subscribed";

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

export function markNewsletterPopupDismissed(): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(DISMISS_KEY, "1");
}

export function shouldShowNewsletterPopup(): boolean {
  if (typeof window === "undefined") return false;
  if (localStorage.getItem(SUBSCRIBED_KEY) === "1") return false;
  if (localStorage.getItem(DISMISS_KEY) === "1") return false;
  return true;
}

export function clearNewsletterSubscribedFlag(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SUBSCRIBED_KEY);
}
