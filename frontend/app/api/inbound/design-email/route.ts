import { NextResponse } from "next/server";

export const runtime = "nodejs";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Inbound email → auto-post designed deal.
 *
 * Wire SendGrid/Mailgun/Cloudflare Email Worker to POST here with JSON:
 * {
 *   "subject": "DESIGN:uuid-here",
 *   "attachment_url": "https://…/creative.jpg",
 *   "body_text": "optional caption",
 *   "secret": "<DESIGN_FULFILL_SECRET>"
 * }
 *
 * Or call the FastAPI endpoint directly:
 * POST /api/v1/design-requests/inbound-email
 */
export async function POST(req: Request) {
  const secret =
    process.env.DESIGN_FULFILL_SECRET ?? "mealdeals-design";

  let body: {
    subject?: string;
    attachment_url?: string;
    body_text?: string;
    secret?: string;
  };

  const contentType = req.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    body = await req.json();
  } else {
    // Form-encoded provider payloads
    const form = await req.formData();
    body = {
      subject: String(form.get("subject") ?? form.get("Subject") ?? ""),
      attachment_url: String(
        form.get("attachment_url") ??
          form.get("attachments") ??
          form.get("attachment") ??
          "",
      ),
      body_text: String(form.get("text") ?? form.get("body") ?? ""),
      secret: String(form.get("secret") ?? secret),
    };
  }

  if (!body.subject || !body.attachment_url) {
    return NextResponse.json(
      { error: "subject and attachment_url are required" },
      { status: 400 },
    );
  }

  const upstream = await fetch(
    `${API_URL.replace(/\/$/, "")}/api/v1/design-requests/inbound-email`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subject: body.subject,
        attachment_url: body.attachment_url,
        body_text: body.body_text,
        secret: body.secret ?? secret,
      }),
    },
  );

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}
