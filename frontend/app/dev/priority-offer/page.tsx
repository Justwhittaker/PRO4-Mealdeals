import { BillingActions } from "@/components/merchant/BillingActions";
import { notFound } from "next/navigation";

/**
 * Local-only preview of Priority offer copy (no Stripe / auth).
 * Visit http://localhost:3000/dev/priority-offer
 */
export default function PriorityOfferPreviewPage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return (
    <main className="mx-auto max-w-2xl space-y-8 px-4 py-12">
      <div>
        <p className="text-[10px] font-medium uppercase tracking-wider text-burgundy-500">
          Local preview
        </p>
        <h1 className="mt-1 font-display text-3xl text-charcoal-50">
          Priority subscription
        </h1>
        <p className="mt-2 text-sm text-charcoal-400">
          Start with a free month (card on file), then £17.17/month. Or pay
          £25.76 now — that&apos;s 3 months at 50% off (£8.59×3), then £17.17/mo.
        </p>
        <p className="mt-2 text-xs text-charcoal-500">
          Checkout buttons are wired but may fail without Stripe/session — copy
          and layout are what to review.
        </p>
      </div>

      <BillingActions
        merchantId="preview-merchant"
        countryCode="GB"
        currency="GBP"
        monthlyAmount={17.17}
        promoAmount={25.76}
        trialEligible
        contactPath="/contact"
        isSubscriber={false}
      />
    </main>
  );
}
