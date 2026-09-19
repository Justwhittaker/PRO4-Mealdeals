import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { getGoRedirectUrl } from "@/lib/api";
import {
  NEWSLETTER_UNLOCK_COOKIE,
  isGoDealId,
} from "@/lib/newsletter-storage";

/**
 * Click-through redirect → backend /go/{deal_id} (affiliate / tracking).
 * Requires newsletter unlock cookie set after signup or email sign-in.
 */
export async function GET(
  req: Request,
  { params }: { params: { deal_id: string } },
) {
  const dealId = params.deal_id;
  if (!dealId || !isGoDealId(dealId)) {
    return NextResponse.json({ error: "Invalid deal id" }, { status: 400 });
  }

  const unlocked =
    cookies().get(NEWSLETTER_UNLOCK_COOKIE)?.value === "1";
  if (!unlocked) {
    const next = `/go/${dealId}`;
    const signup = new URL("/newsletter", req.url);
    signup.searchParams.set("next", next);
    return NextResponse.redirect(signup, { status: 302 });
  }

  const target = getGoRedirectUrl(dealId);
  return NextResponse.redirect(target, { status: 302 });
}
