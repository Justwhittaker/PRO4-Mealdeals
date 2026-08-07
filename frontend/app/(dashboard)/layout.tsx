import { Suspense } from "react";
import Link from "next/link";
import { getServerSession } from "next-auth";
import { LogoutButton } from "@/components/auth/LogoutButton";
import { BrandLogo } from "@/components/landing/BrandLogo";
import { authOptions } from "@/lib/auth";
import { DashboardSignIn } from "./sign-in";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession(authOptions);

  if (!session) {
    return (
      <div className="min-h-screen bg-white">
        <div className="border-b border-charcoal-700 bg-white">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-2 sm:px-6">
            <BrandLogo size="sm" priority />
            <span className="text-xs font-medium uppercase tracking-wider text-charcoal-400">
              Merchant Sign in
            </span>
          </div>
        </div>
        <Suspense fallback={null}>
          <DashboardSignIn />
        </Suspense>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      <div className="border-b border-charcoal-700 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 flex-wrap items-center gap-4">
            <BrandLogo size="sm" priority />
            <nav className="flex flex-wrap gap-4 text-sm text-charcoal-300">
              <Link href="/dashboard" className="hover:text-burgundy-600">
                Deal of the century
              </Link>
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
          </div>
          <div className="flex items-center gap-3">
            <p className="text-sm text-charcoal-400">
              {session.user?.email ?? session.user?.name}
            </p>
            <LogoutButton variant="outline" className="h-8 px-3 text-xs" />
          </div>
        </div>
      </div>
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">{children}</div>
    </div>
  );
}
