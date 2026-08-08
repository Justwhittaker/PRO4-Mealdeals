import { redirect } from "next/navigation";

/**
 * Billing is merged into Deal of the century (upsell) / profile (post-pay).
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

  // Paid checkout → profile; cancel / bare hit → upsell page.
  if (searchParams.success) {
    redirect(qs ? `/dashboard/profile?${qs}` : "/dashboard/profile");
  }
  redirect(qs ? `/dashboard?${qs}` : "/dashboard");
}
