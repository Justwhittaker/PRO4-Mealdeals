import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { LogoutButton } from "@/components/auth/LogoutButton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { authOptions } from "@/lib/auth";
import { fetchMerchantProfile } from "@/lib/api";
import { ProfileForm } from "./profile-form";

export default async function ProfilePage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/dashboard");

  const merchantId = session.user.id;
  const profile = await fetchMerchantProfile(merchantId);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl text-charcoal-50">Profile</h1>
        <p className="mt-2 text-charcoal-400">
          Your venue identity, subscription, and deal history live here so you
          can repost past offers into open Priority slots.
        </p>
      </div>

      {!profile.ok ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Couldn&apos;t load profile ({profile.error}). Start the API at{" "}
          <code className="text-citrus-300">NEXT_PUBLIC_API_URL</code> — signing
          in creates/links a merchant profile automatically.
        </div>
      ) : (
        <ProfileForm merchantId={merchantId} initial={profile.data} />
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Session</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-sm text-charcoal-400">
            Signed in as{" "}
            <span className="text-charcoal-100">
              {session.user?.email ?? session.user?.name ?? "merchant"}
            </span>
          </p>
          <LogoutButton label="Log out of Dine A Deal" />
        </CardContent>
      </Card>
    </div>
  );
}
