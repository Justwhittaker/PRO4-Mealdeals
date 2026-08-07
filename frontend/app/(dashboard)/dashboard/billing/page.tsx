import { redirect } from "next/navigation";

/**
 * Billing is merged into the merchant landing page ("Deal of the century").
 * Keep this route so old Stripe return URLs still work.
 */
export default function BillingRedirectPage({
  searchParams,
}: {
  searchParams: { success?: string; canceled?: string; plan?: string };
}) {
  const params = new URLSearchParams();
  if (searchParams.success) params.set("success", searchParams.success);
  if (searchParams.canceled) params.set("canceled", searchParams.canceled);
  if (searchParams.plan) params.set("plan", searchParams.plan);
  const qs = params.toString();
  redirect(qs ? `/dashboard?${qs}` : "/dashboard");
}
