import Link from "next/link";
import {
  Bell,
  Compass,
  Database,
  MessagesSquare,
  Palette,
  Smartphone,
} from "lucide-react";
import { SiteFooter } from "@/components/landing/SiteFooter";

export const metadata = {
  title: "About us",
  description:
    "Dine a Deal services — digital marketing, SEO, content creation — and the marketing gurus, hoteliers, and developers working for you.",
};

const SERVICES = [
  {
    title: "Digital Marketing",
    icon: Smartphone,
    body: "Digital marketing is incredibly important these days as the use of the Internet, mobile devices, social media, search engines, and other channels are in high demand. Our aim as digital marketers is to reach consumers easily by being visible to them on their connected devices and to use visually appealing content to gain more engagement from your audience.",
  },
  {
    title: "SEO",
    icon: Compass,
    body: "Search engine optimization (SEO) is the process of growing the quality and quantity of website traffic by increasing the visibility of a website or web page to users of a web search engine so that your business listing appears above your competitors for organic results.",
  },
  {
    title: "Content Creation",
    icon: Palette,
    body: "Content creation is the process of generating ideas that appeal to your clientele and customers when creating written or visual content around products and services and making that information accessible to your audience as a blog, video, infographic, and more. We pride ourselves on maximizing your portfolio and giving you fantastic content you can use on any platform.",
  },
] as const;

const WORKING_FOR_YOU = [
  {
    title: "Marketing Gurus",
    icon: MessagesSquare,
    body: "Our team has 22+ years of marketing experience to help you build your brand.",
  },
  {
    title: "Hoteliers",
    icon: Bell,
    body: "Our team has 18+ years of restaurant and hotel experience — get great ideas to boost your business.",
  },
  {
    title: "Developers",
    icon: Database,
    body: "Our team has 16+ years of website design and analytical experience.",
  },
] as const;

export default function AboutPage() {
  return (
    <div className="relative min-h-screen bg-white">
      <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16">
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
          Dine a Deal
        </p>
        <h1 className="mt-2 font-display text-3xl text-charcoal-50 sm:text-4xl">
          About us
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-charcoal-300 sm:text-base">
          We&apos;re all about the thrill of a great deal — hunting down tasty
          savings near you, and giving hotels, businesses, and grocers a
          cheerful, flat-rate stage to shout about their offers (no voucher cut,
          allowing businesses to keep all their earnings).
        </p>

        <section className="mt-14" aria-labelledby="services-heading">
          <h2
            id="services-heading"
            className="font-display text-2xl text-charcoal-50 sm:text-3xl"
          >
            Services
          </h2>
          <ul className="mt-8 grid gap-10 sm:grid-cols-3">
            {SERVICES.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.title}>
                  <p className="flex items-center gap-2 font-display text-lg text-burgundy-600">
                    <Icon className="h-5 w-5 shrink-0" aria-hidden />
                    {item.title}
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-charcoal-300">
                    {item.body}
                  </p>
                </li>
              );
            })}
          </ul>
        </section>

        <section
          className="mt-16 border-t border-charcoal-700 pt-14"
          aria-labelledby="working-heading"
        >
          <h2
            id="working-heading"
            className="font-display text-2xl text-charcoal-50 sm:text-3xl"
          >
            Working for you
          </h2>
          <ul className="mt-8 grid gap-10 sm:grid-cols-3">
            {WORKING_FOR_YOU.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.title}>
                  <p className="flex items-center gap-2 font-display text-lg text-burgundy-600">
                    <Icon className="h-5 w-5 shrink-0" aria-hidden />
                    {item.title}
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-charcoal-300">
                    {item.body}
                  </p>
                </li>
              );
            })}
          </ul>
        </section>

        <p className="mt-14 text-sm text-charcoal-400">
          Want to talk through a campaign?{" "}
          <Link
            href="/contact"
            className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
          >
            Contact us
          </Link>
          .
        </p>
      </main>

      <SiteFooter />
    </div>
  );
}
