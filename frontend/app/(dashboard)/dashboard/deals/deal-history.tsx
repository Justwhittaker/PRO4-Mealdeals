"use client";

import { useState } from "react";
import Link from "next/link";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  deleteMerchantDeal,
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
  initialDeals,
  openSlots: initialOpen,
  activeCount: initialActive,
}: DealHistoryProps) {
  const [deals, setDeals] = useState(initialDeals);
  const [openSlots, setOpenSlots] = useState(initialOpen);
  const [activeCount, setActiveCount] = useState(initialActive);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

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
          ? "Design Special activated."
          : "Deal activated."
        : deal.slot_exempt
          ? "Design Special deactivated."
          : "Deal deactivated — slot freed.",
    );
  }

  async function onConfirmDelete(deal: HistoryDeal) {
    setBusy(deal.id);
    setMessage(null);
    const result = await deleteMerchantDeal(deal.id);
    setBusy(null);
    if (!result.ok) {
      setMessage(result.error);
      return;
    }
    setDeals((prev) => prev.filter((d) => d.id !== deal.id));
    if (deal.is_active && !deal.slot_exempt) {
      setActiveCount((n) => Math.max(0, n - 1));
      setOpenSlots((n) => n + 1);
    }
    setPendingDeleteId(null);
    setMessage("Deal deleted from your profile.");
  }

  if (deals.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-charcoal-300">No deals in your history yet.</p>
          <p className="mt-1 text-sm text-charcoal-500">
            Create a Priority deal — save for later or activate into an open
            slot.
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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-charcoal-400">
          {activeCount} live Priority · {openSlots} open slots · {deals.length} in
          history
        </p>
        <Button asChild size="sm">
          <Link href="/dashboard/deals/new">Create deal</Link>
        </Button>
      </div>
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
          const canActivatePriority =
            !deal.is_active && !deal.slot_exempt && openSlots <= 0;
          const isDeleting = pendingDeleteId === deal.id;
          return (
            <li key={deal.id}>
              <Card>
                <CardContent className="space-y-3 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate font-medium text-charcoal-100">
                          {title}
                        </p>
                        <Badge variant={deal.is_active ? "default" : "secondary"}>
                          {deal.is_active ? "Live" : "Saved for later"}
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
                    <div className="flex flex-wrap items-center gap-2">
                      <Button asChild variant="outline" size="sm">
                        <Link href={`/dashboard/deals/${deal.id}/edit`}>Edit</Link>
                      </Button>
                      {deal.is_active ? (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busy === deal.id}
                          onClick={() => void onToggle(deal)}
                        >
                          {busy === deal.id ? "…" : "Deactivate"}
                        </Button>
                      ) : canActivatePriority ? (
                        <Button
                          size="sm"
                          disabled
                          title="No open Priority slots — deactivate another live deal first, then Activate now"
                        >
                          No open slots
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          disabled={busy === deal.id}
                          onClick={() => void onToggle(deal)}
                        >
                          {busy === deal.id ? "…" : "Activate now"}
                        </Button>
                      )}
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="text-burgundy-400 hover:text-burgundy-300"
                        disabled={busy === deal.id}
                        aria-label={`Delete ${title}`}
                        onClick={() =>
                          setPendingDeleteId(isDeleting ? null : deal.id)
                        }
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  {isDeleting ? (
                    <div className="rounded-md border border-burgundy-400/40 bg-burgundy-500/10 px-3 py-3 text-sm text-charcoal-200">
                      <p className="font-medium text-burgundy-200">
                        Delete this deal permanently?
                      </p>
                      <p className="mt-1 text-charcoal-400">
                        Removing it from your profile also deletes any
                        metric/analytics data for this deal. This cannot be
                        undone.
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-burgundy-400/50 text-burgundy-200"
                          disabled={busy === deal.id}
                          onClick={() => void onConfirmDelete(deal)}
                        >
                          {busy === deal.id ? "Deleting…" : "Yes, delete deal"}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={busy === deal.id}
                          onClick={() => setPendingDeleteId(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
