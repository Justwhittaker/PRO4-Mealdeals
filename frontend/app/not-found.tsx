import Link from "next/link";
import { BrandLogo } from "@/components/landing/BrandLogo";
import { BRAND_NAME } from "@/lib/brand";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center px-4 py-16 text-center sm:px-6">
      <div className="mb-6">
        <BrandLogo size="sm" />
      </div>
      <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
        404
      </p>
      <h1 className="mt-2 font-display text-3xl text-charcoal-50 sm:text-4xl">
        Page not found
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-charcoal-300">
        That country, city, or deal is not on {BRAND_NAME}. Try the homepage or
        search for a city you know.
      </p>
      <Link
        href="/"
        className="mt-8 rounded-md bg-burgundy-500 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-burgundy-600"
      >
        Back to deals
      </Link>
    </main>
  );
}
