import Link from "next/link";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { BRAND_CONTACT_EMAIL } from "@/lib/brand";

export const metadata = {
  title: "Privacy Choices",
  description:
    "Withdraw marketing permission or stop future sale or sharing of your information with CheddaCheeze T/A Dine A Deal.",
};

export default function PrivacyChoicesPage() {
  return (
    <div className="min-h-screen bg-white">
      <main className="mx-auto max-w-2xl px-4 py-12 sm:px-6 sm:py-16">
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
          Privacy
        </p>
        <h1 className="mt-2 font-display text-3xl text-charcoal-50 sm:text-4xl">
          Privacy Choices
        </h1>
        <p className="mt-3 text-sm text-charcoal-300">
          You may withdraw your permission or request that we stop future sale
          or sharing of your personal information at any time.
        </p>

        <div className="mt-8 space-y-4 text-sm leading-relaxed text-charcoal-200">
          <p>To make a request:</p>
          <ul className="list-disc space-y-2 pl-5">
            <li>
              Email{" "}
              <a
                href={`mailto:${BRAND_CONTACT_EMAIL}?subject=${encodeURIComponent("Privacy Choices — stop sale or sharing")}`}
                className="text-burgundy-600 underline-offset-2 hover:underline"
              >
                {BRAND_CONTACT_EMAIL}
              </a>{" "}
              with the subject “Privacy Choices” and the email address you used
              to sign up; or
            </li>
            <li>
              Use the unsubscribe or privacy link in a Dine A Deal email; or
            </li>
            <li>
              Open our{" "}
              <Link
                href="/contact"
                className="text-burgundy-600 underline-offset-2 hover:underline"
              >
                Contact
              </Link>{" "}
              form and ask us to stop future third-party marketing disclosures.
            </li>
          </ul>
          <p>
            Withdrawal will not affect disclosures lawfully completed before
            your request is processed. We will stop future disclosures and take
            any additional steps required by applicable law.
          </p>
          <p>
            Full details are in our{" "}
            <Link
              href="/privacy#third-party-marketing"
              className="text-burgundy-600 underline-offset-2 hover:underline"
            >
              Privacy Notice
            </Link>
            .
          </p>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
