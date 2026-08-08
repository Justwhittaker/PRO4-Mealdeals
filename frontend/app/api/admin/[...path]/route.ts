import { getServerSession } from "next-auth";
import { NextRequest, NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";

const API_URL =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

async function requireAdmin() {
  const session = await getServerSession(authOptions);
  if (!session?.user || session.user.role !== "admin") {
    return null;
  }
  return session;
}

async function proxy(req: NextRequest, pathParts: string[]) {
  const session = await requireAdmin();
  if (!session) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const key = (process.env.ADMIN_API_KEY || "").trim();
  if (!key) {
    return NextResponse.json(
      { detail: "ADMIN_API_KEY is not configured" },
      { status: 503 },
    );
  }

  const subPath = pathParts.join("/");
  const url = new URL(req.url);
  const target = `${API_URL}/api/v1/admin/${subPath}${url.search}`;

  const headers: HeadersInit = {
    Accept: "application/json",
    "X-Admin-Key": key,
  };

  let body: string | undefined;
  if (req.method !== "GET" && req.method !== "HEAD" && req.method !== "DELETE") {
    body = await req.text();
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(target, {
    method: req.method,
    headers,
    body,
    cache: "no-store",
  });

  if (res.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") || "application/json" },
  });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function POST(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function PATCH(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function DELETE(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
