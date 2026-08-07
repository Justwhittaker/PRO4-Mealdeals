"use client";

import { useState } from "react";
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

interface DesignRequestFormProps {
  merchantId: string;
  existing: DesignRequest[];
}

export function DesignRequestForm({
  merchantId,
  existing,
}: DesignRequestFormProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [details, setDetails] = useState("");
  const [photoUrls, setPhotoUrls] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);

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
      setBusy(false);
      return;
    }

    const checkout = await createDesignCheckoutSession(
      created.data.id,
      merchantId,
    );
    if (checkout.url) {
      window.location.href = checkout.url;
      return;
    }

    setError(checkout.error ?? "Could not start payment");
    setBusy(false);
  }

  return (
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
            <Button type="submit" size="lg" disabled={busy} className="w-full">
              {busy ? "Starting checkout…" : "Continue to €20 payment"}
            </Button>
            {error ? <p className="text-sm text-amber-200">{error}</p> : null}
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
                  <Badge variant="outline">{req.status}</Badge>
                </div>
                <p className="mt-1 text-xs text-charcoal-500">
                  DESIGN:{req.id}
                </p>
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
  );
}
