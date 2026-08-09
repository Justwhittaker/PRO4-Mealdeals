import Link from "next/link";
import { CookieSettingsLink } from "@/components/cookie/CookieSettingsLink";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { BRAND_NAME } from "@/lib/brand";

export const metadata = {
  title: "Cookie Policy | Dine A Deal",
  description:
    "How Dine A Deal uses cookies and similar technologies, and how you can manage your preferences.",
};

export default function CookiePolicyPage() {
  return (
    <div className="min-h-screen bg-white print:bg-white">
      <main className="mx-auto max-w-2xl px-4 py-12 sm:px-6 sm:py-16">
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
          Legal
        </p>
        <h1 className="mt-2 font-display text-3xl text-charcoal-50 sm:text-4xl">
          Cookie Policy
        </h1>
        <p className="mt-3 text-sm text-charcoal-300">
          {BRAND_NAME} · How we use cookies
        </p>

        <article className="mt-10 space-y-6 text-sm leading-relaxed text-charcoal-200">
          <section id="overview" className="scroll-mt-24">
            <h2 className="font-display text-xl text-charcoal-50 sm:text-2xl">
              Overview
            </h2>
            <p className="mt-4">
              This Cookie Policy explains how {BRAND_NAME} uses cookies and
              similar technologies on the Platform. It should be read together
              with our{" "}
              <Link
                href="/privacy"
                className="text-burgundy-600 underline-offset-2 hover:underline"
              >
                Privacy Notice
              </Link>{" "}
              and{" "}
              <Link
                href="/terms"
                className="text-burgundy-600 underline-offset-2 hover:underline"
              >
                Terms and Conditions
              </Link>
              .
            </p>
            <p className="mt-4">
              You can review and update non-essential cookie preferences at any
              time using{" "}
              <CookieSettingsLink className="text-burgundy-600 underline-offset-2 hover:underline" />
              .
            </p>
          </section>

          <section id="types" className="scroll-mt-24">
            <h2 className="font-display text-xl text-charcoal-50 sm:text-2xl">
              Types of cookies
            </h2>
            <ul className="mt-4 list-disc space-y-1 pl-5">
              <li>
                Strictly necessary cookies — required for core Platform
                functions such as security, authentication and preference
                storage.
              </li>
              <li>
                Analytics cookies — help us understand how the Platform is used
                so we can improve it (used only where you allow them).
              </li>
              <li>
                Marketing cookies — support advertising and measurement where
                you allow them.
              </li>
            </ul>
          </section>

          <section id="manage" className="scroll-mt-24">
            <h2 className="font-display text-xl text-charcoal-50 sm:text-2xl">
              Managing cookies
            </h2>
            <p className="mt-4">
              You can change your browser settings to block or delete cookies.
              Blocking strictly necessary cookies may affect Platform
              functionality. For optional categories, use{" "}
              <CookieSettingsLink className="text-burgundy-600 underline-offset-2 hover:underline" />{" "}
              on this site.
            </p>
          </section>
        </article>

        <p className="mt-12 text-center text-sm text-charcoal-400">
          <Link href="/terms" className="text-burgundy-600 hover:underline">
            Terms
          </Link>
          {" · "}
          <Link href="/privacy" className="text-burgundy-600 hover:underline">
            Privacy Notice
          </Link>
          {" · "}
          <Link href="/contact" className="text-burgundy-600 hover:underline">
            Contact
          </Link>
          {" · "}
          <Link href="/" className="text-burgundy-600 hover:underline">
            Home
          </Link>
        </p>
      </main>
      <SiteFooter />
    </div>
  );
}
