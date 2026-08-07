import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DESIGN_SPECIAL, DEAL_SLOT_LIMIT } from "@/lib/stripe";
import { formatMoney } from "@/lib/currency";

export function DesignBuyBox() {
  return (
    <Card className="overflow-hidden border-citrus-500/35 bg-gradient-to-br from-charcoal-900 via-charcoal-950 to-charcoal-900">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="featured">Design Deals 4 U</Badge>
          <Badge variant="outline">Slot-exempt</Badge>
          <Badge variant="outline">2 months live</Badge>
        </div>
        <CardTitle className="font-display text-2xl text-charcoal-50 sm:text-3xl">
          Design Deals 4 U —{" "}
          <span className="text-citrus-300">
            {formatMoney(DESIGN_SPECIAL.amount, DESIGN_SPECIAL.currency)}
          </span>{" "}
          per deal
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm leading-relaxed text-charcoal-300">
        <p>
          Submit your title, description, and optional photos. Checkout is a
          one-time {formatMoney(DESIGN_SPECIAL.amount, DESIGN_SPECIAL.currency)}{" "}
          payment link. We design the creative, then email/upload the finished
          attachment — it <strong className="text-charcoal-100">posts automatically</strong>{" "}
          for {DESIGN_SPECIAL.durationDays} days.
        </p>
        <ul className="space-y-2 border-l-2 border-citrus-500/40 pl-4">
          <li>
            Does <strong className="text-citrus-300">not</strong> use your
            Priority subscription slots — you still get{" "}
            <strong className="text-citrus-300">{DEAL_SLOT_LIMIT} posts</strong>{" "}
            with your sub.
          </li>
          <li>
            Designed specials can run for{" "}
            <strong className="text-citrus-300">two months</strong> on the feed.
          </li>
          <li>
            Priority subscriber deals and designed specials can run side by side.
          </li>
        </ul>
      </CardContent>
    </Card>
  );
}
