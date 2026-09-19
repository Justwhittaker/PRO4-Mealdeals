import type { MetadataRoute } from "next";
import { fetchDealsFeed } from "@/lib/api";
import {
  absoluteUrl,
  listingPath,
  sitemapLocationPaths,
  sitemapStaticPaths,
} from "@/lib/seo";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const entries: MetadataRoute.Sitemap = [
    ...sitemapStaticPaths().map((path) => ({
      url: absoluteUrl(path),
      lastModified: now,
      changeFrequency: path === "/" ? ("daily" as const) : ("monthly" as const),
      priority: path === "/" ? 1 : 0.4,
    })),
    ...sitemapLocationPaths().map((path) => ({
      url: absoluteUrl(path),
      lastModified: now,
      changeFrequency: "daily" as const,
      priority: path.split("/").filter(Boolean).length === 1 ? 0.8 : 0.7,
    })),
  ];

  const feed = await fetchDealsFeed({ limit: 10000, autoScrape: false });
  if (feed.ok) {
    const seen = new Set<string>();
    for (const deal of feed.data) {
      const path = listingPath(deal.country, deal.city, deal.id);
      if (seen.has(path)) continue;
      seen.add(path);
      entries.push({
        url: absoluteUrl(path),
        lastModified: deal.createdAt ? new Date(deal.createdAt) : now,
        changeFrequency: "weekly",
        priority: 0.6,
      });
    }
  }

  return entries;
}
