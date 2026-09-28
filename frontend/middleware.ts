import { NextResponse, type NextRequest } from "next/server";
import {
  LOCATION_COOKIE,
  LOCATION_SOURCE_COOKIE,
  canonicalizePublicPathname,
  locationCookieValue,
  resolveGeoFromHeaders,
} from "@/lib/geo";

/**
 * When edge geo headers are present and the visitor hasn't searched a city,
 * stamp a geo preference cookie so homepage / feeds stay local (e.g. US → New York).
 *
 * Also 308-redirect mixed-case / legacy `/gb` URLs onto the lowercase canonical
 * path so Google consolidates duplicates instead of soft-matching them.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const canonicalPath = canonicalizePublicPathname(pathname);
  if (canonicalPath && canonicalPath !== pathname) {
    const url = request.nextUrl.clone();
    url.pathname = canonicalPath;
    return NextResponse.redirect(url, 308);
  }

  const existingSource = request.cookies.get(LOCATION_SOURCE_COOKIE)?.value;
  // Never override an explicit city search
  if (existingSource === "search") {
    return NextResponse.next();
  }

  const target = resolveGeoFromHeaders(request.headers);
  if (!target) {
    return NextResponse.next();
  }

  const value = locationCookieValue(target);
  const current = request.cookies.get(LOCATION_COOKIE)?.value;
  if (current === value && existingSource === "geo") {
    return NextResponse.next();
  }

  const response = NextResponse.next();
  response.cookies.set(LOCATION_COOKIE, value, {
    path: "/",
    maxAge: 60 * 60 * 24 * 180,
    sameSite: "lax",
  });
  response.cookies.set(LOCATION_SOURCE_COOKIE, "geo", {
    path: "/",
    maxAge: 60 * 60 * 24 * 180,
    sameSite: "lax",
  });
  return response;
}

export const config = {
  matcher: [
    "/",
    "/((?!_next/static|_next/image|favicon.ico|robots\\.txt|sitemap\\.xml|sitemaps/|sitemap/|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|txt|html)$).*)",
  ],
};
