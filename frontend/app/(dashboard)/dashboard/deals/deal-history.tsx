"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  repostDeal,
  setDealActive,
  type HistoryDeal,
} from "@/lib/api";
import { formatMoney, type CurrencyCode } from "@/lib/currency";

interface DealHistoryProps {
  merchantId: string;
  initialDeals: HistoryDeal[];
  openSlots: number;
  activeCount: number;
}

export function DealHistory({
  merchantId,
  initialDeals,
  openSlots: initialOpen,
  activeCount: initialActive,
}: DealHistoryProps) {
  const [deals, setDeals] = useState(initialDeals);
  const [openSlots, setOpenSlots] = useState(initialOpen);
  const [activeCount, setActiveCount] = useState(initialActive);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function onRepost(dealId: string) {
    setBusy(dealId);
    setMessage(null);
    const result = await repostDeal(merchantId, dealId);
    setBusy(null);
    if (!result.ok) {
      setMessage(result.error);
      return;
    }
    setMessage(result.data.message);
    setOpenSlots((n) => Math.max(0, n - 1));
    setActiveCount((n) => n + 1);
    window.location.reload();
  }

  async function onToggle(deal: HistoryDeal) {
    setBusy(deal.id);
    setMessage(null);
    const next = !deal.is_active;
    const result = await setDealActive(deal.id, next);
    setBusy(null);
    if (!result.ok) {
      setMessage(result.error);
      return;
    }
    setDeals((prev) =>
      prev.map((d) => (d.id === deal.id ? { ...d, is_active: next } : d)),
    );
    // Design Specials are slot_exempt — they never consume Priority slots.
    if (!deal.slot_exempt) {
      setActiveCount((n) => n + (next ? 1 : -1));
      setOpenSlots((n) => n + (next ? -1 : 1));
    }
    setMessage(
      next
        ? deal.slot_exempt
          ? "Design Special reactivated."
          : "Deal activated."
        : deal.slot_exempt
          ? "Design Special archived."
          : "Deal archived — slot freed.",
    );
  }

  if (deals.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-charcoal-300">No deals in your history yet.</p>
          <p className="mt-1 text-sm text-charcoal-500">
            Create a Priority deal — it stays on your profile forever for reposting.
          </p>
          <Button asChild className="mt-6">
            <Link href="/dashboard/deals/new">Create deal</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-charcoal-400">
        {activeCount} live Priority · {openSlots} open slots · {deals.length} in
        history
      </p>
      {message ? (
        <p className="text-sm text-citrus-200">{message}</p>
      ) : null}
      <ul className="space-y-3">
        {deals.map((deal) => {
          const title =
            deal.title ||
            deal.translations?.[0]?.title ||
            `Deal ${deal.id.slice(0, 8)}`;
          const currency = (deal.currency_code || "EUR").toUpperCase() as CurrencyCode;
          const canReactivatePriority =
            !deal.is_active && !deal.slot_exempt && openSlots <= 0;
          return (
            <li key={deal.id}>
              <Card>
                <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-charcoal-100 truncate">
                        {title}
                      </p>
                      <Badge variant={deal.is_active ? "default" : "secondary"}>
                        {deal.is_active ? "Live" : "History"}
                      </Badge>
                      {deal.slot_exempt ? (
                        <Badge variant="outline">Design Special</Badge>
                      ) : null}
                      {deal.reposted_from_id ? (
                        <Badge variant="outline">Repost</Badge>
                      ) : null}
                    </div>
                    <p className="text-sm text-charcoal-400">
                      {formatMoney(deal.deal_price, currency)}
                      {deal.original_price > deal.deal_price ? (
                        <span className="ml-2 line-through">
                          {formatMoney(deal.original_price, currency)}
                        </span>
                      ) : null}
                      <span className="ml-2 text-charcoal-600">
                        {new Date(deal.created_at).toLocaleDateString()}
                      </span>
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={
                        busy === deal.id ||
                        (canReactivatePriority && !deal.is_active)
                      }
                      onClick={() => onToggle(deal)}
                      title={
                        canReactivatePriority
                          ? "No open Priority slots — archive another deal first"
                          : undefined
                      }
                    >
                      {deal.is_active ? "Archive" : "Reactivate"}
                    </Button>
                    {!deal.is_active && !deal.slot_exempt ? (
                      <Button
                        size="sm"
                        disabled={busy === deal.id || openSlots <= 0}
                        onClick={() => onRepost(deal.id)}
                      >
                        {busy === deal.id ? "…" : "Repost"}
                      </Button>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
