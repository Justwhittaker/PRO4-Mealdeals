"use client";

import { useState } from "react";
import { createCustomerPortalSession } from "@/actions/stripe";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface CustomerPortalCardProps {
  stripeCustomerId?: string | null;
}

export function CustomerPortalCard({
  stripeCustomerId,
}: CustomerPortalCardProps) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function openPortal() {
    setLoading(true);
    setError(null);
    const customerId = stripeCustomerId?.trim() ?? "";
    if (!customerId) {
      setError(
        "No Stripe customer on this profile yet — complete Priority checkout first, then reopen the portal.",
      );
      setLoading(false);
      return;
    }
    try {
      const result = await createCustomerPortalSession(customerId);
      if (result.url) {
        window.location.assign(result.url);
        return;
      }
      setError(result.error ?? "Portal failed");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not open the Stripe customer portal.",
      );
    }
    setLoading(false);
  }

  return (
    <div className="space-y-2">
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <p className="font-medium text-charcoal-100">Customer Portal</p>
            <p className="text-sm text-charcoal-500">
              Update payment method, invoices, or cancel.
            </p>
          </div>
          <Button
            variant="outline"
            disabled={loading}
            onClick={() => void openPortal()}
          >
            {loading ? "Opening…" : "Open portal"}
          </Button>
        </CardContent>
      </Card>
      {error ? (
        <p className="text-sm text-amber-800" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
