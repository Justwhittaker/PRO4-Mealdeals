import { NextResponse } from "next/server";
import { fetchDealSitemapPage } from "@/lib/api";
import {
  absoluteUrl,
  listingPath,
  sitemapLocationPaths,
  sitemapStaticPaths,
} from "@/lib/seo";

export const revalidate = 3600;
export const runtime = "nodejs";

const DEALS_PER_SITEMAP = 2500;
const SITEMAP_PAGE_SIZE = 500;

function urlEntry(
  loc: string,
  lastmod: string,
  changefreq: string,
  priority: string,
): string {
  return `  <url>
    <loc>${loc}</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>${changefreq}</changefreq>
    <priority>${priority}</priority>
  </url>`;
}

function xmlResponse(entries: string[]): NextResponse {
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${entries.join("\n")}
</urlset>`;
  return new NextResponse(body, {
    status: 200,
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}

/**
 * Chunked sitemaps:
 * - /sitemaps/static.xml — home, legal, countries, cities
 * - /sitemaps/deals-0.xml … — deal detail pages
 */
export async function GET(
  _req: Request,
  { params }: { params: { id: string } },
) {
  const now = new Date().toISOString();
  const id = params.id.replace(/\.xml$/i, "");

  if (id === "static") {
    const entries = [
      ...sitemapStaticPaths().map((path) =>
        urlEntry(
          absoluteUrl(path),
          now,
          path === "/" ? "daily" : "monthly",
          path === "/" ? "1.0" : "0.4",
        ),
      ),
      ...sitemapLocationPaths().map((path) =>
        urlEntry(
          absoluteUrl(path),
          now,
          "daily",
          path.split("/").filter(Boolean).length === 1 ? "0.8" : "0.7",
        ),
      ),
    ];
    return xmlResponse(entries);
  }

  const dealMatch = /^deals-(\d+)$/.exec(id);
  if (!dealMatch) {
    return new NextResponse("Not found", { status: 404 });
  }

  const chunk = Number.parseInt(dealMatch[1]!, 10);
  const start = chunk * DEALS_PER_SITEMAP;
  const end = start + DEALS_PER_SITEMAP;
  const deals: { path: string; lastmod: string }[] = [];
  const seen = new Set<string>();

  for (let offset = start; offset < end; offset += SITEMAP_PAGE_SIZE) {
    const page = await fetchDealSitemapPage({
      offset,
      limit: Math.min(SITEMAP_PAGE_SIZE, end - offset),
    });
    if (!page.ok) {
      return xmlResponse([]);
    }
    if (page.data.results.length === 0) break;
    for (const deal of page.data.results) {
      const path = listingPath(deal.country, deal.city, deal.id);
      if (seen.has(path)) continue;
      seen.add(path);
      deals.push({
        path,
        lastmod: deal.createdAt
          ? new Date(deal.createdAt).toISOString()
          : now,
      });
    }
    if (page.data.results.length < SITEMAP_PAGE_SIZE) break;
  }

  if (deals.length === 0 && chunk > 0) {
    return new NextResponse("Not found", { status: 404 });
  }

  return xmlResponse(
    deals.map((deal) =>
      urlEntry(absoluteUrl(deal.path), deal.lastmod, "weekly", "0.6"),
    ),
  );
}
