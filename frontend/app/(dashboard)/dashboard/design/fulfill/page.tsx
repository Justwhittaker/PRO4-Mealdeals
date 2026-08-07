import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { FulfillForm } from "./fulfill-form";

/**
 * Ops tool: paste request id + designed image URL → posts slot-exempt 60-day deal.
 * Prefer inbound email (subject DESIGN:{id}) when wired; this is the manual path.
 */
export default async function DesignFulfillPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/dashboard");

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="font-display text-3xl text-charcoal-50">
          Fulfill design
        </h1>
        <p className="mt-2 text-charcoal-400">
          Upload/link the finished creative. Posts automatically for 2 months and
          does not touch Priority slots. Or email with subject{" "}
          <code className="text-citrus-300">DESIGN:&#123;request-id&#125;</code>.
        </p>
      </div>
      <FulfillForm />
    </div>
  );
}
