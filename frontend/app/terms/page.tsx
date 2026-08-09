import Link from "next/link";
import { LegalRichText } from "@/components/legal/LegalRichText";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { legalConfig, TERMS_VERSION } from "@/lib/legal-config";
import termsSections from "@/lib/terms-sections-data.json";

export const metadata = {
  title: "Terms and Conditions | Dine A Deal",
  description:
    "Terms governing the use of Dine A Deal by consumers, venues, advertisers and business users.",
};

type TermsBlock =
  | { type: "p"; text: string }
  | { type: "ul"; items: string[] };

type TermsSection = {
  number: number;
  id: string;
  title: string;
  tocLabel: string;
  blocks: TermsBlock[];
};

const sections = termsSections as TermsSection[];

export default function TermsAndConditionsPage() {
  return (
    <div className="min-h-screen bg-white print:bg-white">
      <a
        href="#terms-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:shadow"
      >
        Skip to terms content
      </a>
      <main className="mx-auto max-w-2xl px-4 py-12 sm:px-6 sm:py-16 print:max-w-none print:px-0 print:py-4">
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500 print:text-black">
          Legal
        </p>
        <h1 className="mt-2 font-display text-3xl text-charcoal-50 sm:text-4xl print:text-black">
          Dine A Deal Terms and Conditions
        </h1>
        <p className="mt-3 text-sm text-charcoal-300 print:text-black">
          <span className="block sm:inline">
            Effective date: {legalConfig.effectiveDate}
          </span>
          <span className="hidden sm:inline print:inline"> · </span>
          <span className="block sm:inline">
            Last updated: {legalConfig.lastUpdated}
          </span>
          <span className="hidden sm:inline print:inline"> · </span>
          <span className="block sm:inline">Version: {TERMS_VERSION}</span>
        </p>

        <nav
          className="mt-8 print:hidden"
          aria-label="Terms and Conditions table of contents"
        >
          <h2 className="font-display text-lg text-charcoal-50">
            Table of contents
          </h2>
          <ol className="mt-3 columns-1 gap-x-8 space-y-1.5 text-sm text-burgundy-600 sm:columns-2">
            {sections.map((section) => (
              <li key={section.id} className="break-inside-avoid">
                <a
                  href={`#${section.id}`}
                  className="hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-burgundy-500"
                >
                  {section.tocLabel}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <article
          id="terms-content"
          className="mt-10 space-y-10 text-sm leading-relaxed text-charcoal-200 print:text-black"
        >
          {sections.map((section) => (
            <section
              key={section.id}
              id={section.id}
              className="scroll-mt-24"
              aria-labelledby={`${section.id}-heading`}
            >
              <h2
                id={`${section.id}-heading`}
                className="font-display text-xl text-charcoal-50 sm:text-2xl print:text-black"
              >
                {section.title}
              </h2>
              <div className="mt-4 space-y-4">
                {section.blocks.map((block, index) => {
                  if (block.type === "ul") {
                    return (
                      <ul
                        key={`${section.id}-ul-${index}`}
                        className="list-disc space-y-1 pl-5"
                      >
                        {block.items.map((item, itemIndex) => (
                          <li key={`${section.id}-li-${index}-${itemIndex}`}>
                            <LegalRichText text={item} />
                          </li>
                        ))}
                      </ul>
                    );
                  }
                  return (
                    <p key={`${section.id}-p-${index}`}>
                      <LegalRichText text={block.text} />
                    </p>
                  );
                })}
              </div>
            </section>
          ))}
        </article>

        <p className="mt-12 text-center text-sm text-charcoal-400 print:hidden">
          <Link href="/privacy" className="text-burgundy-600 hover:underline">
            Privacy Notice
          </Link>
          {" · "}
          <Link href="/cookies" className="text-burgundy-600 hover:underline">
            Cookie Policy
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
      <div className="print:hidden">
        <SiteFooter />
      </div>
    </div>
  );
}
