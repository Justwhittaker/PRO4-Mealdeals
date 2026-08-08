import Link from "next/link";
import { ContactForm } from "@/components/contact/ContactForm";
import { BrandLogo } from "@/components/landing/BrandLogo";
import { SiteFooter } from "@/components/landing/SiteFooter";

export const metadata = {
  title: "Contact us",
  description:
    "Contact Dine A Deal about Priority subscriptions, free-month eligibility, or billing.",
};

export default function ContactPage() {
  return (
    <div className="min-h-screen max-w-[100vw] overflow-x-clip bg-white">
      <main className="mx-auto max-w-xl px-4 py-12 text-center sm:px-6 sm:py-16">
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
          Support
        </p>
        <h1 className="mt-2 font-display text-3xl text-charcoal-50 sm:text-4xl">
          Contact us
        </h1>
        <p className="mx-auto mt-3 max-w-prose text-sm text-charcoal-300">
          Free Priority months can only be used once per email, business name,
          or venue location. If registration failed and you think that&apos;s
          wrong — or you need help with billing — send us a message below.
        </p>

        <div className="mt-8 text-left">
          <ContactForm />
        </div>

        <p className="mt-8 text-sm text-charcoal-400">
          <Link href="/dashboard" className="text-burgundy-600 hover:underline">
            Deal of the century
          </Link>
          {" · "}
          <Link href="/" className="text-burgundy-600 hover:underline">
            Home
          </Link>
        </p>

        <div className="mt-12 flex justify-center opacity-95">
          <BrandLogo size="lg" href={null} className="max-w-full" />
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
