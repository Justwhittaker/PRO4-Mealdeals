import { NextResponse } from "next/server";
import { fetchDealSitemapPage } from "@/lib/api";
import { absoluteUrl } from "@/lib/seo";

export const revalidate = 3600;
export const runtime = "nodejs";

const DEALS_PER_SITEMAP = 2500;

async function dealChunkCount(): Promise<number> {
  const page = await fetchDealSitemapPage({ offset: 0, limit: 1 });
  if (!page.ok || page.data.total <= 0) return 1;
  return Math.max(1, Math.ceil(page.data.total / DEALS_PER_SITEMAP));
}

/** Sitemap index — Google Search Console submits this URL. */
export async function GET() {
  const now = new Date().toISOString();
  const dealChunks = await dealChunkCount();
  const parts = [
    absoluteUrl("/sitemaps/static.xml"),
    ...Array.from({ length: dealChunks }, (_, i) =>
      absoluteUrl(`/sitemaps/deals-${i}.xml`),
    ),
  ];

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${parts
  .map(
    (loc) => `  <sitemap>
    <loc>${loc}</loc>
    <lastmod>${now}</lastmod>
  </sitemap>`,
  )
  .join("\n")}
</sitemapindex>`;

  return new NextResponse(body, {
    status: 200,
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
