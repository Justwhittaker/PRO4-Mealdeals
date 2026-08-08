"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { createDesignCheckoutSession } from "@/actions/stripe";
import {
  createDesignRequest,
  type DesignRequest,
} from "@/lib/api";
import { DESIGN_SPECIAL } from "@/lib/stripe";
import { formatMoney } from "@/lib/currency";

interface DesignRequestFormProps {
  merchantId: string;
  existing: DesignRequest[];
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending_payment: "Pending payment",
    paid: "Paid",
    in_design: "In design",
    posted: "Posted",
    cancelled: "Cancelled",
    draft: "Draft",
  };
  return labels[status] ?? status.replace(/_/g, " ");
}

export function DesignRequestForm({
  merchantId,
  existing,
}: DesignRequestFormProps) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [details, setDetails] = useState("");
  const [photoUrls, setPhotoUrls] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const cart = useMemo(
    () => existing.filter((req) => req.status === "pending_payment"),
    [existing],
  );

  async function startCheckout(requestId: string) {
    setBusy(requestId);
    setError(null);
    setMessage(null);
    const checkout = await createDesignCheckoutSession(requestId, merchantId);
    if (checkout.url) {
      window.location.href = checkout.url;
      return;
    }
    setError(checkout.error ?? "Could not start payment");
    setBusy(null);
  }

  async function createRequest(payNow: boolean) {
    if (!title.trim() || !description.trim()) {
      setError("Add a deal title and short description first.");
      return;
    }

    setBusy(payNow ? "checkout" : "save");
    setError(null);
    setMessage(null);

    const urls = photoUrls
      .split(/[\n,]/)
      .map((u) => u.trim())
      .filter(Boolean)
      .slice(0, 8);

    const created = await createDesignRequest({
      merchant_id: merchantId,
      title,
      description,
      details,
      photo_urls: urls,
    });

    if (!created.ok) {
      setError(created.error);
      setBusy(null);
      return;
    }

    if (payNow) {
      await startCheckout(created.data.id);
      return;
    }

    setTitle("");
    setDescription("");
    setDetails("");
    setPhotoUrls("");
    setBusy(null);
    setMessage(
      "Saved to your design cart — pay whenever you’re ready from Pending payment below.",
    );
    router.refresh();
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    await createRequest(true);
  }

  return (
    <div className="space-y-6">
      {cart.length > 0 ? (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardHeader className="pb-2">
            <CardTitle className="flex flex-wrap items-center gap-2 text-base">
              Design cart
              <Badge variant="outline">
                {cart.length} pending payment
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-charcoal-300">
              Finish checkout when you’re ready —{" "}
              {formatMoney(DESIGN_SPECIAL.amount, DESIGN_SPECIAL.currency)} per
              designed deal.
            </p>
            <ul className="space-y-2">
              {cart.map((req) => (
                <li
                  key={req.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-charcoal-700 bg-charcoal-950/60 px-3 py-3"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-charcoal-100">{req.title}</p>
                    <p className="text-xs text-charcoal-500">
                      DESIGN:{req.id}
                    </p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    disabled={busy !== null}
                    onClick={() => void startCheckout(req.id)}
                  >
                    {busy === req.id
                      ? "Opening checkout…"
                      : `Pay ${formatMoney(DESIGN_SPECIAL.amount, DESIGN_SPECIAL.currency)}`}
                  </Button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle>Request a designed deal</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">Deal title</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  placeholder="Lunch for two — Friday special"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Short description</Label>
                <textarea
                  id="description"
                  required
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="flex w-full rounded-md border border-charcoal-700 bg-charcoal-950 px-3 py-2 text-sm text-charcoal-100 placeholder:text-charcoal-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-citrus-500/40"
                  placeholder="What the customer gets…"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="details">Design brief / details</Label>
                <textarea
                  id="details"
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                  rows={5}
                  className="flex w-full rounded-md border border-charcoal-700 bg-charcoal-950 px-3 py-2 text-sm text-charcoal-100 placeholder:text-charcoal-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-citrus-500/40"
                  placeholder="Brand colours, offer rules, tone, must-include text…"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="photos">Optional photo URLs</Label>
                <textarea
                  id="photos"
                  value={photoUrls}
                  onChange={(e) => setPhotoUrls(e.target.value)}
                  rows={3}
                  className="flex w-full rounded-md border border-charcoal-700 bg-charcoal-950 px-3 py-2 text-sm text-charcoal-100 placeholder:text-charcoal-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-citrus-500/40"
                  placeholder="One URL per line (food shots, logo, etc.)"
                />
                <p className="text-xs text-charcoal-500">
                  Paste hosted image links for now (S3, Drive public link, etc.).
                </p>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Button
                  type="submit"
                  size="lg"
                  disabled={busy !== null}
                  className="w-full sm:flex-1"
                >
                  {busy === "checkout"
                    ? "Starting checkout…"
                    : `Continue to ${formatMoney(DESIGN_SPECIAL.amount, DESIGN_SPECIAL.currency)} payment`}
                </Button>
                <Button
                  type="button"
                  size="lg"
                  variant="outline"
                  disabled={busy !== null}
                  className="w-full sm:flex-1"
                  onClick={() => void createRequest(false)}
                >
                  {busy === "save" ? "Saving…" : "Save to cart — pay later"}
                </Button>
              </div>
              {error ? <p className="text-sm text-amber-200">{error}</p> : null}
              {message ? (
                <p className="text-sm text-citrus-200">{message}</p>
              ) : null}
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Your design requests</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {existing.length === 0 ? (
              <p className="text-sm text-charcoal-500">No requests yet.</p>
            ) : (
              existing.map((req) => (
                <div
                  key={req.id}
                  className="rounded-lg border border-charcoal-700 bg-charcoal-950/50 p-3 text-sm"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium text-charcoal-100">{req.title}</p>
                    <Badge
                      variant={
                        req.status === "pending_payment" ? "secondary" : "outline"
                      }
                    >
                      {statusLabel(req.status)}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-charcoal-500">
                    DESIGN:{req.id}
                  </p>
                  {req.status === "pending_payment" ? (
                    <Button
                      type="button"
                      size="sm"
                      className="mt-3"
                      disabled={busy !== null}
                      onClick={() => void startCheckout(req.id)}
                    >
                      {busy === req.id
                        ? "Opening checkout…"
                        : `Pay now — ${formatMoney(DESIGN_SPECIAL.amount, DESIGN_SPECIAL.currency)}`}
                    </Button>
                  ) : null}
                </div>
              ))
            )}
            <p className="text-xs text-charcoal-500">
              After payment, email the finished creative with subject{" "}
              <code className="text-citrus-300">DESIGN:&#123;id&#125;</code> — it
              auto-posts for 60 days without using a Priority slot.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
