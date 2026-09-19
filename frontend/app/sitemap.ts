import type { MetadataRoute } from "next";
import { fetchDealsFeed } from "@/lib/api";
import {
  absoluteUrl,
  listingPath,
  sitemapLocationPaths,
  sitemapStaticPaths,
} from "@/lib/seo";

export const revalidate = 3600;

/** Keep each sitemap under ~1MB so Googlebot can fetch reliably. */
const DEALS_PER_SITEMAP = 2500;

type DealSitemapItem = {
  country: string;
  city: string;
  id: string;
  createdAt?: string;
};

async function loadUniqueDeals(): Promise<DealSitemapItem[]> {
  const feed = await fetchDealsFeed({ limit: 10000, autoScrape: false });
  if (!feed.ok) return [];
  const seen = new Set<string>();
  const deals: DealSitemapItem[] = [];
  for (const deal of feed.data) {
    const path = listingPath(deal.country, deal.city, deal.id);
    if (seen.has(path)) continue;
    seen.add(path);
    deals.push({
      country: deal.country,
      city: deal.city,
      id: deal.id,
      createdAt: deal.createdAt,
    });
  }
  return deals;
}

/**
 * Split into /sitemap/0.xml (static + cities) and /sitemap/1.xml… (deals).
 * Next.js serves /sitemap.xml as the index.
 */
export async function generateSitemaps() {
  const deals = await loadUniqueDeals();
  const dealChunks = Math.max(1, Math.ceil(deals.length / DEALS_PER_SITEMAP));
  return Array.from({ length: 1 + dealChunks }, (_, id) => ({ id }));
}

export default async function sitemap({
  id,
}: {
  id: number | string;
}): Promise<MetadataRoute.Sitemap> {
  const chunkId = typeof id === "string" ? Number.parseInt(id, 10) : id;
  const now = new Date();

  if (chunkId === 0) {
    return [
      ...sitemapStaticPaths().map((path) => ({
        url: absoluteUrl(path),
        lastModified: now,
        changeFrequency:
          path === "/" ? ("daily" as const) : ("monthly" as const),
        priority: path === "/" ? 1 : 0.4,
      })),
      ...sitemapLocationPaths().map((path) => ({
        url: absoluteUrl(path),
        lastModified: now,
        changeFrequency: "daily" as const,
        priority: path.split("/").filter(Boolean).length === 1 ? 0.8 : 0.7,
      })),
    ];
  }

  const deals = await loadUniqueDeals();
  const start = (chunkId - 1) * DEALS_PER_SITEMAP;
  const slice = deals.slice(start, start + DEALS_PER_SITEMAP);

  return slice.map((deal) => ({
    url: absoluteUrl(listingPath(deal.country, deal.city, deal.id)),
    lastModified: deal.createdAt ? new Date(deal.createdAt) : now,
    changeFrequency: "weekly" as const,
    priority: 0.6,
  }));
}
