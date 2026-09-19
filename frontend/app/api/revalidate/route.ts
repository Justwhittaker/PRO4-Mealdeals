import { revalidatePath, revalidateTag } from "next/cache";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type RevalidateBody = {
  secret?: string;
  tags?: string[];
  paths?: string[];
};

/**
 * On-demand ISR invalidation — called by the Celery worker after scrape ingest.
 * Requires REVALIDATE_SECRET matching the backend REVALIDATE_SECRET.
 */
export async function POST(req: Request) {
  const expected = process.env.REVALIDATE_SECRET?.trim();
  if (!expected) {
    return NextResponse.json(
      { error: "REVALIDATE_SECRET is not configured" },
      { status: 503 },
    );
  }

  let body: RevalidateBody;
  try {
    body = (await req.json()) as RevalidateBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  if (body.secret !== expected) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const tags = Array.from(
    new Set((body.tags ?? []).map((t) => t.trim()).filter(Boolean)),
  );
  const paths = Array.from(
    new Set((body.paths ?? []).map((p) => p.trim()).filter(Boolean)),
  );

  for (const tag of tags) {
    revalidateTag(tag);
  }
  for (const path of paths) {
    revalidatePath(path);
  }

  return NextResponse.json({
    revalidated: true,
    tags,
    paths,
    at: new Date().toISOString(),
  });
}
