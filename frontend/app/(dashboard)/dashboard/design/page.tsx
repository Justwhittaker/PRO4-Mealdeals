import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { listDesignRequests } from "@/lib/api";
import { DESIGN_SPECIAL } from "@/lib/stripe";
import { DesignBuyBox } from "./design-buy-box";
import { DesignRequestForm } from "./design-request-form";

export default async function DesignPage({
  searchParams,
}: {
  searchParams: { paid?: string; canceled?: string; request?: string };
}) {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/dashboard");

  const merchantId = session.user.id;
  const history = await listDesignRequests(merchantId);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl text-charcoal-50">
          Design Deals 4 U
        </h1>
        <p className="mt-2 max-w-2xl text-charcoal-400">
          Send a brief and optional photos — we design the creative, you pay{" "}
          {DESIGN_SPECIAL.amount}€, and we post it for two months. Slot-exempt —
          does not use your Priority posts.
        </p>
      </div>

      {searchParams.paid ? (
        <div className="rounded-lg border border-citrus-500/30 bg-citrus-500/10 px-4 py-3 text-sm text-citrus-200">
          Payment received
          {searchParams.request ? (
            <>
              {" "}
              for request{" "}
              <code className="text-citrus-300">{searchParams.request}</code>
            </>
          ) : null}
          . We&apos;ll design your deal and post it automatically — reply or
          email the finished file with subject{" "}
          <code className="text-citrus-300">
            DESIGN:{searchParams.request ?? "{request-id}"}
          </code>
          .
        </div>
      ) : null}
      {searchParams.canceled ? (
        <div className="rounded-lg border border-charcoal-600 bg-charcoal-900/60 px-4 py-3 text-sm text-charcoal-300">
          Checkout canceled — no charge was made. Your request stays in the
          design cart below so you can pay later.
        </div>
      ) : null}

      <DesignBuyBox />

      <DesignRequestForm
        merchantId={merchantId}
        existing={history.ok ? history.data.results : []}
      />
    </div>
  );
}
