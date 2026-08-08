import Link from "next/link";
import { SiteFooter } from "@/components/landing/SiteFooter";

export const metadata = {
  title: "Partner information",
  description:
    "Categories of third-party marketing recipients for CheddaCheeze T/A Dine A Deal.",
};

const CATEGORIES = [
  "Retail and consumer products",
  "Restaurants, hospitality and travel",
  "Entertainment and events",
  "Technology and digital services",
  "Advertising and marketing",
  "Competitions and promotional offers",
  "Market research",
] as const;

export default function PrivacyPartnersPage() {
  return (
    <div className="min-h-screen bg-white">
      <main className="mx-auto max-w-2xl px-4 py-12 sm:px-6 sm:py-16">
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
          Privacy
        </p>
        <h1 className="mt-2 font-display text-3xl text-charcoal-50 sm:text-4xl">
          Partner information
        </h1>
        <p className="mt-3 text-sm text-charcoal-300">
          Current categories of third-party businesses that may receive
          personal information when you opt in to compensated data sharing,
          as described in our{" "}
          <Link
            href="/privacy#third-party-marketing"
            className="text-burgundy-600 underline-offset-2 hover:underline"
          >
            Privacy Notice
          </Link>
          .
        </p>

        <ul className="mt-8 list-disc space-y-2 pl-5 text-sm text-charcoal-200">
          {CATEGORIES.map((category) => (
            <li key={category}>{category}</li>
          ))}
        </ul>

        <p className="mt-6 text-sm text-charcoal-400">
          Where applicable law requires us to name individual recipients, we
          will update this page. For questions, use{" "}
          <Link href="/privacy/choices" className="text-burgundy-600 hover:underline">
            Privacy Choices
          </Link>{" "}
          or{" "}
          <Link href="/contact" className="text-burgundy-600 hover:underline">
            Contact
          </Link>
          .
        </p>
      </main>
      <SiteFooter />
    </div>
  );
}
