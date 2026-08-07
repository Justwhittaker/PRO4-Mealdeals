"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { fulfillDesignRequest } from "@/lib/api";

export function FulfillForm() {
  const [requestId, setRequestId] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    const result = await fulfillDesignRequest(requestId.trim(), {
      image_url: imageUrl.trim(),
      title: title.trim() || undefined,
      currency_code: "EUR",
    });
    setBusy(false);
    if (!result.ok) {
      setMessage(result.error);
      return;
    }
    setMessage(
      `${result.data.message} Deal id: ${result.data.deal.id}`,
    );
  }

  return (
    <Card>
      <CardContent className="p-6">
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="rid">Design request id</Label>
            <Input
              id="rid"
              value={requestId}
              onChange={(e) => setRequestId(e.target.value)}
              required
              placeholder="uuid from DESIGN:{id}"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="img">Finished creative URL</Label>
            <Input
              id="img"
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
              required
              placeholder="https://…/deal.jpg"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="title">Override title (optional)</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Posting…" : "Post designed deal (60 days)"}
          </Button>
          {message ? (
            <p className="text-sm text-citrus-200">{message}</p>
          ) : null}
        </form>
      </CardContent>
    </Card>
  );
}
