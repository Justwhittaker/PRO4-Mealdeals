import { Suspense } from "react";
import Link from "next/link";
import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { LogoutButton } from "@/components/auth/LogoutButton";
import { authOptions } from "@/lib/auth";
import { fetchMerchantProfile } from "@/lib/api";
import { DashboardSignIn } from "./sign-in";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession(authOptions);

  if (session?.user?.role === "admin") {
    redirect("/admin");
  }

  if (!session) {
    // Global SiteHeader already shows the brand — no second logo strip.
    return (
      <div className="min-h-screen max-w-[100vw] overflow-x-clip bg-white">
        <Suspense fallback={null}>
          <DashboardSignIn />
        </Suspense>
      </div>
    );
  }

  const profile = await fetchMerchantProfile(session.user.id);
  const isSubscriber = profile.ok ? profile.data.is_subscriber : false;

  return (
    <div className="min-h-screen max-w-[100vw] overflow-x-clip bg-white">
      <div className="border-b border-charcoal-700 bg-white">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-center gap-3 px-3 py-3 text-center sm:justify-between sm:px-6 sm:text-left">
          <nav className="flex flex-wrap justify-center gap-x-4 gap-y-2 text-sm text-charcoal-300">
            {!isSubscriber ? (
              <Link href="/dashboard" className="hover:text-burgundy-600">
                Deal of the century
              </Link>
            ) : null}
            <Link href="/dashboard/profile" className="hover:text-burgundy-600">
              Profile
            </Link>
            <Link href="/dashboard/deals" className="hover:text-burgundy-600">
              Deals
            </Link>
            <Link
              href="/dashboard/deals/new"
              className="hover:text-burgundy-600"
            >
              New deal
            </Link>
            <Link href="/dashboard/design" className="hover:text-burgundy-600">
              Design Deals 4 U
            </Link>
          </nav>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <p className="text-sm text-charcoal-400">
              {session.user?.email ?? session.user?.name}
            </p>
            <LogoutButton variant="outline" className="h-8 px-3 text-xs" />
          </div>
        </div>
      </div>
      <div className="mx-auto w-full max-w-5xl px-3 py-8 sm:px-6 sm:py-10">
        {children}
      </div>
    </div>
  );
}
