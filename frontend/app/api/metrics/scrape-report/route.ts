import { NextResponse } from "next/server";

const API_URL =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

/** Public proxy for live scrape inventory (no admin auth). */
export async function GET() {
  try {
    const res = await fetch(`${API_URL}/api/v1/scrapers/report`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("Content-Type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch (err) {
    return NextResponse.json(
      {
        detail:
          err instanceof Error ? err.message : "Scrape report API unreachable",
      },
      { status: 502 },
    );
  }
}
