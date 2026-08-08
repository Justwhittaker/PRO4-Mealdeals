"use client";

import { DealCard, type DealCardProps } from "@/components/deals/DealCard";
import { Button } from "@/components/ui/button";

interface DealPreviewDialogProps {
  open: boolean;
  deal: DealCardProps;
  publishing?: boolean;
  canActivate?: boolean;
  activateBlockedReason?: string | null;
  onKeepEditing: () => void;
  onSaveForLater: () => void;
  onConfirmActivate: () => void;
}

/** Full-screen overlay — shows how the deal card will look on the public site. */
export function DealPreviewDialog({
  open,
  deal,
  publishing = false,
  canActivate = true,
  activateBlockedReason = null,
  onKeepEditing,
  onSaveForLater,
  onConfirmActivate,
}: DealPreviewDialogProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[200] flex items-end justify-center bg-black/50 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="deal-preview-title"
    >
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="Close preview"
        onClick={onKeepEditing}
      />
      <div className="relative z-10 w-full max-w-md overflow-hidden rounded-md border border-charcoal-700 bg-white shadow-deal">
        <div className="border-b border-charcoal-800 px-4 py-3">
          <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
            Preview
          </p>
          <h2
            id="deal-preview-title"
            className="font-display text-xl text-charcoal-50"
          >
            How your deal will look
          </h2>
          <p className="mt-1 text-sm text-charcoal-400">
            This is the card shoppers see in the feed and on your area page.
          </p>
        </div>

        <div className="bg-charcoal-950/40 p-4">
          <div className="pointer-events-none">
            <DealCard {...deal} />
          </div>
        </div>

        <div className="space-y-3 border-t border-charcoal-800 p-4">
          {canActivate ? (
            <>
              <Button
                type="button"
                className="w-full"
                disabled={publishing}
                onClick={onConfirmActivate}
              >
                {publishing ? "Saving…" : "Confirm & activate now"}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="w-full"
                disabled={publishing}
                onClick={onSaveForLater}
              >
                {publishing ? "Saving…" : "Save for later"}
              </Button>
            </>
          ) : (
            <>
              <Button
                type="button"
                className="w-full"
                disabled
                title={activateBlockedReason ?? undefined}
              >
                No open slots
              </Button>
              <Button
                type="button"
                className="w-full"
                disabled={publishing}
                onClick={onSaveForLater}
              >
                {publishing ? "Saving…" : "Save for later — add to profile"}
              </Button>
            </>
          )}
          <Button
            type="button"
            variant="ghost"
            className="w-full"
            disabled={publishing}
            onClick={onKeepEditing}
          >
            Keep editing
          </Button>
          <p className="text-center text-xs text-charcoal-500">
            {canActivate
              ? "Save for later keeps the deal on your profile as inactive — it won't appear on the public site until you activate it."
              : "All Priority slots are full. Save for later adds this deal to your profile inactive so you can schedule Activate now when a slot opens."}
          </p>
        </div>
      </div>
    </div>
  );
}
