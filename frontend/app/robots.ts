import type { MetadataRoute } from "next";
import { absoluteUrl } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  const disallow = [
    "/dashboard",
    "/admin",
    "/api/",
    "/go/",
    "/live-metrics.html",
    "/newsletter/unsubscribe",
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
