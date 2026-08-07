import { NextResponse } from "next/server";
import { getGoRedirectUrl } from "@/lib/api";

/**
 * Click-through redirect → backend /go/{deal_id} (affiliate / tracking).
 */
export async function GET(
  _req: Request,
  { params }: { params: { deal_id: string } },
) {
  const dealId = params.deal_id;
  if (!dealId) {
    return NextResponse.json({ error: "Missing deal id" }, { status: 400 });
  }

  const target = getGoRedirectUrl(dealId);
  return NextResponse.redirect(target, { status: 302 });
}
