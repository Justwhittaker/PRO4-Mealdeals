import type { MetadataRoute } from "next";
import { absoluteUrl } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  // Keep private app surfaces blocked. Do NOT block `/go/` — Google must crawl
  // redirects to consolidate link signals ("Page with redirect" is expected).
  // `/newsletter/unsubscribe` already sends noindex; blocking it in robots.txt
  // only hides that signal from Google.
  const disallow = [
    "/dashboard",
    "/admin",
    "/api/",
    "/live-metrics.html",
  ];

  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow,
      },
      {
        userAgent: "Googlebot",
        allow: "/",
        disallow,
      },
      {
        userAgent: "AdsBot-Google",
        allow: "/",
        disallow,
      },
      {
        userAgent: "Mediapartners-Google",
        allow: "/",
        disallow,
      },
    ],
    sitemap: absoluteUrl("/sitemap.xml"),
  };
}
