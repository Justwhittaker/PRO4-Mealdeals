import { Facebook, Twitter } from "lucide-react";

function TripAdvisorIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden
    >
      <path d="M12.006 4.295c-2.67 0-5.338.784-7.645 2.353H0l1.914 2.088A8.296 8.296 0 0 0 0 14.48a8.303 8.303 0 0 0 8.302 8.302 8.25 8.25 0 0 0 3.698-.87 8.287 8.287 0 0 0 3.7.87 8.303 8.303 0 0 0 8.302-8.302 8.286 8.286 0 0 0-1.914-5.743L24 6.648h-4.361A15.13 15.13 0 0 0 12.006 4.295zm0 2.608c2.006 0 3.915.52 5.588 1.486a6.3 6.3 0 0 0-.88-.058 6.703 6.703 0 0 0-6.702 6.702c0 1.52.51 2.922 1.37 4.06a6.67 6.67 0 0 1-.376.01 6.703 6.703 0 0 1-6.702-6.701 6.703 6.703 0 0 1 6.702-6.702v1.203zm0 3.09a3.61 3.61 0 0 1 3.61 3.61 3.61 3.61 0 0 1-3.61 3.61 3.61 3.61 0 0 1-3.61-3.61 3.61 3.61 0 0 1 3.61-3.61zm7.697 1.003a3.61 3.61 0 0 1 3.61 3.61 3.61 3.61 0 0 1-3.61 3.61 3.61 3.61 0 0 1-3.61-3.61 3.61 3.61 0 0 1 3.61-3.61zM12 11.42a2.183 2.183 0 1 0 .002 4.366A2.183 2.183 0 0 0 12 11.42zm7.697 1.003a2.183 2.183 0 1 0 0 4.366 2.183 2.183 0 0 0 0-4.366z" />
    </svg>
  );
}

const SOCIAL = [
  {
    label: "Twitter / X",
    href: "https://twitter.com",
    icon: Twitter,
  },
  {
    label: "Facebook",
    href: "https://facebook.com",
    icon: Facebook,
  },
] as const;

export function SiteFooter() {
  return (
    <footer className="border-t border-charcoal-700 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 py-8 sm:px-6">
        <div className="flex items-center gap-6">
          {SOCIAL.map(({ label, href, icon: Icon }) => (
            <a
              key={label}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={label}
              className="text-charcoal-300 transition hover:text-burgundy-500"
            >
              <Icon className="h-6 w-6" />
            </a>
          ))}
          <a
            href="https://www.tripadvisor.com"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="TripAdvisor"
            className="text-charcoal-300 transition hover:text-burgundy-500"
          >
            <TripAdvisorIcon className="h-6 w-6" />
          </a>
        </div>
        <nav
          className="flex items-center gap-4 text-xs uppercase tracking-wider text-charcoal-400"
          aria-label="Footer"
        >
          <a
            href="/about"
            className="transition hover:text-burgundy-500"
          >
            About us
          </a>
          <a
            href="/newsletter"
            className="transition hover:text-burgundy-500"
          >
            Weekly specials
          </a>
          <a
            href="/contact"
            className="transition hover:text-burgundy-500"
          >
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
