"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  createMerchantDeal,
  previewValueCalculator,
  updateMerchantDeal,
  type MerchantDealDetail,
} from "@/lib/api";
import {
  currenciesAlphabetical,
  formatMoney,
  isCurrencyCode,
  type CurrencyCode,
} from "@/lib/currency";

interface LineItem {
  name: string;
  value: number;
}

interface NewDealFormProps {
  merchantId: string;
  openSlots: number;
  isSubscriber?: boolean;
  mode?: "create" | "edit";
  dealId?: string;
  initialDeal?: MerchantDealDetail;
}

const MAX_IMAGE_BYTES = 900_000;

function guessCategory(name: string): string {
  const n = name.toLowerCase();
  if (n.includes("drink") || n.includes("coffee") || n.includes("soda")) {
    return "drink";
  }
  if (n.includes("side") || n.includes("fries") || n.includes("salad")) {
    return "side";
  }
  return "main";
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") resolve(reader.result);
      else reject(new Error("Could not read image"));
    };
    reader.onerror = () => reject(new Error("Could not read image"));
    reader.readAsDataURL(file);
  });
}

function initialItemsFromDeal(deal?: MerchantDealDetail): LineItem[] {
  if (!deal?.items?.length) {
    return [
      { name: "Main", value: 10 },
      { name: "Drink", value: 3.5 },
      { name: "Side", value: 3 },
    ];
  }
  return deal.items.map((item) => ({
    name: item.item_name,
    value: Number(item.individual_price),
  }));
}

export function NewDealForm({
  merchantId,
  openSlots,
  isSubscriber = true,
  mode = "create",
  dealId,
  initialDeal,
}: NewDealFormProps) {
  const router = useRouter();
  const currencyOptions = useMemo(() => currenciesAlphabetical(), []);
  const translation = initialDeal?.translations?.[0];
  const [title, setTitle] = useState(
    initialDeal?.title || translation?.title || "",
  );
  const [description, setDescription] = useState(
    initialDeal?.description || translation?.description || "",
  );
  const [dealPrice, setDealPrice] = useState(
    initialDeal ? Number(initialDeal.deal_price) : 12,
  );
  const initialCurrency = (initialDeal?.currency_code || "GBP").toUpperCase();
  const [currency, setCurrency] = useState<CurrencyCode>(
    isCurrencyCode(initialCurrency) ? initialCurrency : "GBP",
  );
  const [imageUrl, setImageUrl] = useState(initialDeal?.image_url ?? "");
  const [items, setItems] = useState<LineItem[]>(() =>
    initialItemsFromDeal(initialDeal),
  );
  const [preview, setPreview] = useState<{
    marketValue: number;
    savings: number;
    savingsPercent: number;
  } | null>(null);
  const [pending, startTransition] = useTransition();
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const isEdit = mode === "edit";

  useEffect(() => {
    const handle = setTimeout(() => {
      startTransition(async () => {
        const result = await previewValueCalculator({
          dealPrice,
          items: items.filter((i) => i.name && i.value > 0),
          currency,
        });
        if (result.ok) {
          setPreview({
            marketValue: result.data.marketValue,
            savings: result.data.savings,
            savingsPercent: result.data.savingsPercent,
          });
        }
      });
    }, 200);
    return () => clearTimeout(handle);
  }, [dealPrice, items, currency]);

  function updateItem(index: number, patch: Partial<LineItem>) {
    setItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
  }

  function addItem() {
    setItems((prev) => [...prev, { name: "", value: 0 }]);
  }

  function removeItem(index: number) {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }

  async function applyImageFile(file: File | null | undefined) {
    if (!file) return;
    const okType =
      file.type === "image/png" ||
      file.type === "image/jpeg" ||
      file.type === "image/webp" ||
      /\.(png|jpe?g|webp)$/i.test(file.name);
    if (!okType) {
      setError("Use a PNG, JPG, or WebP image.");
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setError("Image must be under ~900KB. Compress it or use an image URL.");
      return;
    }
    try {
      const dataUrl = await readFileAsDataUrl(file);
      setImageUrl(dataUrl);
      setError(null);
    } catch {
      setError("Could not read that image file.");
    }
  }

  async function onPublish() {
    setError(null);
    if (!title.trim()) {
      setError("Add a deal title.");
      return;
    }
    if (!isSubscriber) {
      setError(
        "Choose a Priority subscription on Deal of the century before adding a deal.",
      );
      return;
    }
    if (!isEdit && openSlots <= 0) {
      setError(
        "No open Priority slots. Deactivate a live deal or upgrade on Deal of the century.",
      );
      return;
    }
    const lineItems = items.filter((i) => i.name.trim() && i.value > 0);
    if (lineItems.length === 0) {
      setError("Add at least one included item with a value.");
      return;
    }

    const original =
      preview?.marketValue ??
      lineItems.reduce((sum, i) => sum + i.value, 0);

    const mappedItems = lineItems.map((i) => ({
      item_name: i.name.trim(),
      individual_price: i.value,
      category: guessCategory(i.name),
    }));

    setPublishing(true);
    const result =
      isEdit && dealId
        ? await updateMerchantDeal(dealId, {
            title: title.trim(),
            description: description.trim() || title.trim(),
            deal_price: dealPrice,
            original_price: original,
            currency_code: currency,
            image_url: imageUrl.trim() || null,
            items: mappedItems,
          })
        : await createMerchantDeal({
            merchant_id: merchantId,
            title: title.trim(),
            description: description.trim() || title.trim(),
            deal_price: dealPrice,
            original_price: original,
            currency_code: currency,
            image_url: imageUrl.trim() || null,
            items: mappedItems,
          });
    setPublishing(false);

    if (!result.ok) {
      setError(result.error);
      return;
    }
    router.push("/dashboard/deals");
    router.refresh();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <Card>
        <CardHeader>
          <CardTitle>{isEdit ? "Edit deal" : "Deal details"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="rounded-lg border border-citrus-500/20 bg-citrus-500/5 px-3 py-2 text-sm text-charcoal-300">
            Priority plan includes{" "}
            <strong className="text-citrus-300">3 active slots</strong>
            {openSlots >= 0 ? (
              <>
                {" "}
                ·{" "}
                <span className="text-citrus-300">{openSlots} open</span>
              </>
            ) : null}
            . Subscriber deals rank above auto-scraped external listings.{" "}
            <a
              href="/dashboard"
              className="text-citrus-300 underline-offset-2 hover:underline"
            >
              Deal of the century
            </a>
            .
          </p>
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              placeholder="Weekday lunch set"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="flex w-full rounded-md border border-charcoal-700 bg-charcoal-950 px-3 py-2 text-sm text-charcoal-100 placeholder:text-charcoal-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-citrus-500/40"
              placeholder="What the customer gets…"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="image-url">Deal photo</Label>
            <Input
              id="image-url"
              type="url"
              placeholder="https://… or drop a PNG below"
              value={imageUrl.startsWith("data:") ? "" : imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
            />
            <div
              className={`rounded-md border border-dashed px-4 py-6 text-center text-sm transition-colors ${
                dragOver
                  ? "border-citrus-400 bg-citrus-500/10 text-citrus-200"
                  : "border-charcoal-700 bg-charcoal-950 text-charcoal-400"
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                void applyImageFile(e.dataTransfer.files?.[0]);
              }}
            >
              <p>Drop a PNG / JPG here, or choose a file</p>
              <Input
                type="file"
                accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
                className="mt-3 cursor-pointer border-0 bg-transparent px-0 file:mr-3 file:rounded-md file:border-0 file:bg-charcoal-800 file:px-3 file:py-1.5 file:text-charcoal-100"
                onChange={(e) => void applyImageFile(e.target.files?.[0])}
              />
              {imageUrl ? (
                <div className="mt-4 space-y-2">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imageUrl}
                    alt="Deal preview"
                    className="mx-auto max-h-40 rounded-md object-cover"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setImageUrl("")}
                  >
                    Remove photo
                  </Button>
                </div>
              ) : null}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="price">Deal price</Label>
              <Input
                id="price"
                type="number"
                min={0}
                step={0.5}
                value={dealPrice}
                onChange={(e) => setDealPrice(Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Currency</Label>
              <Select
                value={currency}
                onValueChange={(v) => setCurrency(v as CurrencyCode)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  {currencyOptions.map(({ code, label }) => (
                    <SelectItem key={code} value={code}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Included items (à la carte value)</Label>
              <Button type="button" variant="ghost" size="sm" onClick={addItem}>
                Add item
              </Button>
            </div>
            {items.map((item, index) => (
              <div
                key={index}
                className="grid grid-cols-[1fr_100px_auto] gap-2"
              >
                <Input
                  placeholder="Item name"
                  value={item.name}
                  onChange={(e) => updateItem(index, { name: e.target.value })}
                />
                <Input
                  type="number"
                  min={0}
                  step={0.5}
                  value={item.value}
                  onChange={(e) =>
                    updateItem(index, { value: Number(e.target.value) })
                  }
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeItem(index)}
                  aria-label={`Remove ${item.name || "item"}`}
                >
                  Remove
                </Button>
              </div>
            ))}
          </div>

          <Button
            type="button"
            className="w-full sm:w-auto"
            disabled={publishing || (!isEdit && openSlots <= 0)}
            onClick={() => void onPublish()}
          >
            {publishing
              ? isEdit
                ? "Saving…"
                : "Publishing…"
              : !isEdit && openSlots <= 0
                ? "No open slots"
                : isEdit
                  ? "Save changes"
                  : "Publish deal"}
          </Button>
          {error ? <p className="text-sm text-amber-200">{error}</p> : null}
        </CardContent>
      </Card>

      <Card className="h-fit border-citrus-500/25 lg:sticky lg:top-24">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Value calculator
            {pending ? (
              <span className="animate-pulse-soft text-xs font-normal text-charcoal-500">
                Updating…
              </span>
            ) : null}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-charcoal-500">
              Your price
            </p>
            <p className="mt-1 font-display text-2xl text-charcoal-50">
              {formatMoney(dealPrice, currency)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-charcoal-500">
              Market value
            </p>
            <p className="mt-1 font-display text-2xl text-charcoal-50">
              {preview ? formatMoney(preview.marketValue, currency) : "—"}
            </p>
          </div>
          <div className="rounded-lg bg-citrus-400/10 px-4 py-3">
            <p className="text-xs uppercase tracking-wider text-citrus-400/80">
              Customer saves
            </p>
            <p className="mt-1 font-display text-3xl text-citrus-300">
              {preview
                ? `${formatMoney(preview.savings, currency)} (${preview.savingsPercent}%)`
                : "—"}
            </p>
          </div>
          {title ? (
            <p className="text-sm text-charcoal-400">
              Preview: <span className="text-charcoal-200">{title}</span>
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
