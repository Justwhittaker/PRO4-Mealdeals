import { Facebook, Instagram } from "lucide-react";

const SOCIAL = [
  {
    label: "Instagram (coming soon)",
    href: "#instagram",
    icon: Instagram,
    external: false,
  },
  {
    label: "Facebook",
    href: "https://facebook.com",
    icon: Facebook,
    external: true,
  },
] as const;

export function SiteFooter() {
  return (
    <footer className="border-t border-charcoal-700 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 py-8 sm:px-6">
        <div className="flex items-center gap-6">
          {SOCIAL.map(({ label, href, icon: Icon, external }) => (
            <a
              key={label}
              href={href}
              {...(external
                ? { target: "_blank", rel: "noopener noreferrer" }
                : {})}
              aria-label={label}
              className="text-charcoal-300 transition hover:text-burgundy-500"
            >
              <Icon className="h-6 w-6" />
            </a>
          ))}
        </div>
        <nav
          className="flex items-center gap-4 text-xs uppercase tracking-wider text-charcoal-400"
          aria-label="Footer"
        >
          <a href="/about" className="transition hover:text-burgundy-500">
            About us
          </a>
          <a
            href="/newsletter"
            className="transition hover:text-burgundy-500"
          >
            Weekly specials
          </a>
          <a href="/contact" className="transition hover:text-burgundy-500">
            Contact
          </a>
        </nav>
        <p className="text-center text-xs uppercase tracking-wider text-charcoal-400">
          Dine A Deal · Flat-rate restaurant advertising
        </p>
      </div>
    </footer>
  );
}
