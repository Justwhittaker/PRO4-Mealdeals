"use client";

import { DealCard, type DealCardProps } from "@/components/deals/DealCard";
import { Button } from "@/components/ui/button";

interface DealPreviewDialogProps {
  open: boolean;
  deal: DealCardProps;
  /** compose = activate/save CTAs; view = close-only history preview */
  mode?: "compose" | "view";
  publishing?: boolean;
  canActivate?: boolean;
  activateBlockedReason?: string | null;
  onKeepEditing: () => void;
  onSaveForLater?: () => void;
  onConfirmActivate?: () => void;
}

/** Full-screen overlay — shows how the deal card will look on the public site. */
export function DealPreviewDialog({
  open,
  deal,
  mode = "compose",
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
      <div className="relative z-10 flex max-h-[min(92vh,720px)] w-full max-w-md flex-col overflow-hidden rounded-md border border-charcoal-700 bg-white shadow-deal">
        <div className="shrink-0 border-b border-charcoal-800 px-4 py-3">
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

        <div className="min-h-0 flex-1 overflow-y-auto bg-charcoal-950/40 p-4">
          <div className="pointer-events-none">
            <DealCard {...deal} />
          </div>
        </div>

        <div className="shrink-0 space-y-3 border-t border-charcoal-800 p-4">
          {mode === "view" ? (
            <Button
              type="button"
              className="w-full"
              onClick={onKeepEditing}
            >
              Close preview
            </Button>
          ) : canActivate ? (
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
                Save for later keeps the deal on your profile as inactive — it
                won&apos;t appear on the public site until you activate it.
              </p>
            </>
          ) : (
            <>
              <Button
                type="button"
                className="w-full"
                disabled={publishing}
                onClick={onSaveForLater}
              >
                {publishing ? "Saving…" : "Save for later — add to profile"}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="w-full"
                disabled
                title={activateBlockedReason ?? undefined}
              >
                No open slots
              </Button>
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
                All Priority slots are full. Save for later adds this deal to
                your profile inactive so you can Activate now when a slot opens.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
