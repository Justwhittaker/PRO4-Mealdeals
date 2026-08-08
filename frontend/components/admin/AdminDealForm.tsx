"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { staffFetch } from "@/lib/admin-client";
import type { AdminDeal } from "@/lib/admin-api";

type DealFormProps = {
  mode: "create" | "edit";
  merchantId: string;
  initial?: AdminDeal | null;
};

export function AdminDealForm({ mode, merchantId, initial }: DealFormProps) {
  const router = useRouter();
  const [title, setTitle] = useState(initial?.translations?.[0]?.title ?? "");
  const [description, setDescription] = useState(
    initial?.translations?.[0]?.description ?? "",
  );
  const [dealPrice, setDealPrice] = useState(String(initial?.deal_price ?? ""));
  const [originalPrice, setOriginalPrice] = useState(
    String(initial?.original_price ?? ""),
  );
  const [currency, setCurrency] = useState(initial?.currency_code ?? "EUR");
  const [imageUrl, setImageUrl] = useState(initial?.image_url ?? "");
  const [venueCategory, setVenueCategory] = useState(
    initial?.venue_category ?? "",
  );
  const [isActive, setIsActive] = useState(initial?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const payload = {
      merchant_id: merchantId,
      title: title.trim(),
      description: description.trim(),
      deal_price: Number(dealPrice) || 0,
      original_price: Number(originalPrice) || Number(dealPrice) || 0,
      currency_code: currency.trim().toUpperCase() || "EUR",
      image_url: imageUrl.trim() || null,
      venue_category: venueCategory.trim() || null,
      is_active: isActive,
      language_code: "en",
      items: [],
    };

    const result =
      mode === "create"
        ? await staffFetch<AdminDeal>("deals", {
            method: "POST",
            body: JSON.stringify(payload),
          })
        : await staffFetch<AdminDeal>(`deals/${initial!.id}`, {
            method: "PATCH",
            body: JSON.stringify(payload),
          });

    setSaving(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }

    router.push(`/admin/merchants/${merchantId}`);
    router.refresh();
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-xl space-y-4">
      <div className="space-y-2">
        <Label htmlFor="title">Title</Label>
        <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} required />
      </div>
      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <textarea
          id="description"
          className="min-h-[120px] w-full rounded-md border border-charcoal-700 bg-transparent px-3 py-2 text-sm"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="deal">Deal price</Label>
          <Input
            id="deal"
            type="number"
            step="0.01"
            min="0"
            value={dealPrice}
            onChange={(e) => setDealPrice(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="original">Original price</Label>
          <Input
            id="original"
            type="number"
            step="0.01"
            min="0"
            value={originalPrice}
            onChange={(e) => setOriginalPrice(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="currency">Currency</Label>
          <Input
            id="currency"
            value={currency}
            maxLength={3}
            onChange={(e) => setCurrency(e.target.value)}
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="image">Image URL</Label>
        <Input id="image" value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="category">Venue category</Label>
        <Input
          id="category"
          value={venueCategory}
          onChange={(e) => setVenueCategory(e.target.value)}
        />
      </div>
      <div className="flex items-center gap-2">
        <input
          id="active"
          type="checkbox"
          checked={isActive}
          onChange={(e) => setIsActive(e.target.checked)}
        />
        <Label htmlFor="active">Active on website</Label>
      </div>
      {error ? <p className="text-sm text-burgundy-600">{error}</p> : null}
      <Button type="submit" disabled={saving}>
        {saving ? "Saving…" : mode === "create" ? "Create deal" : "Save deal"}
      </Button>
    </form>
  );
}
