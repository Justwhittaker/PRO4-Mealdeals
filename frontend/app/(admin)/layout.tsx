import Link from "next/link";
import { getServerSession } from "next-auth";
import { LogoutButton } from "@/components/auth/LogoutButton";
import { authOptions } from "@/lib/auth";
import { AdminSignIn } from "./admin/sign-in";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession(authOptions);

  if (!session || session.user.role !== "admin") {
    return (
      <div className="min-h-screen max-w-[100vw] overflow-x-clip bg-white">
        <AdminSignIn />
      </div>
    );
  }

  return (
    <div className="min-h-screen max-w-[100vw] overflow-x-clip bg-white">
      <div className="border-b border-charcoal-700 bg-white">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-center gap-3 px-3 py-3 text-center sm:justify-between sm:px-6 sm:text-left">
          <nav className="flex flex-wrap justify-center gap-x-4 gap-y-2 text-sm text-charcoal-300">
            <Link href="/admin" className="font-medium text-charcoal-50 hover:text-burgundy-600">
              Merchants
            </Link>
            <Link href="/admin/deals" className="hover:text-burgundy-600">
              All deals
            </Link>
            <Link href="/live-metrics.html" className="hover:text-burgundy-600">
              Live metrics
            </Link>
            <Link href="/" className="hover:text-burgundy-600">
              Public site
            </Link>
          </nav>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <p className="text-sm text-charcoal-400">
              Admin · {session.user?.email}
            </p>
            <LogoutButton
              variant="outline"
              className="h-8 px-3 text-xs"
              label="Log out"
            />
          </div>
        </div>
      </div>
      <div className="mx-auto w-full max-w-5xl px-3 py-8 sm:px-6 sm:py-10">
        {children}
      </div>
    </div>
  );
}
