"use client";

import { useEffect, useState, useTransition } from "react";
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
import { createMerchantDeal, previewValueCalculator } from "@/lib/api";
import {
  CURRENCIES,
  formatMoney,
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
}

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

export function NewDealForm({
  merchantId,
  openSlots,
  isSubscriber = true,
}: NewDealFormProps) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dealPrice, setDealPrice] = useState(12);
  const [currency, setCurrency] = useState<CurrencyCode>("GBP");
  const [items, setItems] = useState<LineItem[]>([
    { name: "Main", value: 10 },
    { name: "Drink", value: 3.5 },
    { name: "Side", value: 3 },
  ]);
  const [preview, setPreview] = useState<{
    marketValue: number;
    savings: number;
    savingsPercent: number;
  } | null>(null);
  const [pending, startTransition] = useTransition();
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    if (openSlots <= 0) {
      setError(
        "No open Priority slots. Archive a live deal or upgrade on Deal of the century.",
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

    setPublishing(true);
    const result = await createMerchantDeal({
      merchant_id: merchantId,
      title: title.trim(),
      description: description.trim() || title.trim(),
      deal_price: dealPrice,
      original_price: original,
      currency_code: currency,
      items: lineItems.map((i) => ({
        item_name: i.name.trim(),
        individual_price: i.value,
        category: guessCategory(i.name),
      })),
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
          <CardTitle>Deal details</CardTitle>
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
                <SelectContent>
                  {(Object.keys(CURRENCIES) as CurrencyCode[]).map((code) => (
                    <SelectItem key={code} value={code}>
                      {CURRENCIES[code].symbol} {code}
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
              <div key={index} className="grid grid-cols-[1fr_100px] gap-2">
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
              </div>
            ))}
          </div>

          <Button
            type="button"
            className="w-full sm:w-auto"
            disabled={publishing || openSlots <= 0}
            onClick={onPublish}
          >
            {publishing
              ? "Publishing…"
              : openSlots <= 0
                ? "No open slots"
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
