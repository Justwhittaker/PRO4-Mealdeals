"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { staffFetch } from "@/lib/admin-client";
import type { AdminDeal, AdminMerchant } from "@/lib/admin-api";

export function MerchantAdminPanel({
  merchant,
  deals,
}: {
  merchant: AdminMerchant;
  deals: AdminDeal[];
}) {
  const router = useRouter();
  const [name, setName] = useState(merchant.name);
  const [email, setEmail] = useState(merchant.email ?? "");
  const [phone, setPhone] = useState(merchant.phone ?? "");
  const [website, setWebsite] = useState(merchant.website ?? "");
  const [bio, setBio] = useState(merchant.bio ?? "");
  const [isSubscriber, setIsSubscriber] = useState(merchant.is_subscriber);
  const [tier, setTier] = useState(merchant.tier_level);
  const [slots, setSlots] = useState(String(merchant.deal_slot_limit ?? 0));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    const result = await staffFetch<AdminMerchant>(`merchants/${merchant.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        name: name.trim(),
        email: email.trim() || null,
        phone: phone.trim() || null,
        website: website.trim() || null,
        bio: bio.trim() || null,
        is_subscriber: isSubscriber,
        tier_level: tier,
        deal_slot_limit: Number(slots) || 0,
        subscription_phase: isSubscriber ? "monthly" : "none",
      }),
    });
    setSaving(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setMessage("Profile saved.");
    router.refresh();
  }

  async function onDeleteAccount() {
    const ok = window.confirm(
      `Delete merchant "${merchant.name}" and ALL their deals from the website? This cannot be undone.`,
    );
    if (!ok) return;
    setSaving(true);
    setError(null);
    const result = await staffFetch<void>(`merchants/${merchant.id}`, {
      method: "DELETE",
    });
    setSaving(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    router.push("/admin");
    router.refresh();
  }

  async function onDeleteDeal(dealId: string, title: string) {
    const ok = window.confirm(`Delete deal "${title}" permanently?`);
    if (!ok) return;
    const result = await staffFetch<void>(`deals/${dealId}`, { method: "DELETE" });
    if (!result.ok) {
      setError(result.error);
      return;
    }
    router.refresh();
  }

  async function onToggleDeal(deal: AdminDeal) {
    const result = await staffFetch<AdminDeal>(`deals/${deal.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !deal.is_active }),
    });
    if (!result.ok) {
      setError(result.error);
      return;
    }
    router.refresh();
  }

  return (
    <div className="space-y-10">
      <form onSubmit={onSave} className="space-y-4 rounded-lg border border-charcoal-700 p-4">
        <h2 className="font-display text-xl text-charcoal-50">Edit profile</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="phone">Phone</Label>
            <Input id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="website">Website</Label>
            <Input id="website" value={website} onChange={(e) => setWebsite(e.target.value)} />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="bio">Bio</Label>
            <textarea
              id="bio"
              className="min-h-[90px] w-full rounded-md border border-charcoal-700 bg-transparent px-3 py-2 text-sm"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              id="subscriber"
              type="checkbox"
              checked={isSubscriber}
              onChange={(e) => setIsSubscriber(e.target.checked)}
            />
            <Label htmlFor="subscriber">Active subscriber</Label>
          </div>
          <div className="space-y-2">
            <Label htmlFor="tier">Tier</Label>
            <select
              id="tier"
              className="w-full rounded-md border border-charcoal-700 bg-transparent px-3 py-2 text-sm"
              value={tier}
              onChange={(e) => setTier(e.target.value)}
            >
              <option value="free">free</option>
              <option value="featured">featured</option>
              <option value="enterprise">enterprise</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="slots">Deal slot limit (0–3)</Label>
            <Input
              id="slots"
              type="number"
              min={0}
              max={3}
              value={slots}
              onChange={(e) => setSlots(e.target.value)}
            />
          </div>
        </div>
        {error ? <p className="text-sm text-burgundy-600">{error}</p> : null}
        {message ? <p className="text-sm text-emerald-700">{message}</p> : null}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save profile"}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="border-burgundy-600 text-burgundy-600"
            disabled={saving}
            onClick={onDeleteAccount}
          >
            Delete account
          </Button>
        </div>
      </form>

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-display text-xl text-charcoal-50">Deals</h2>
            <p className="text-sm text-charcoal-400">
              {deals.length} total · staff creates are slot-exempt
            </p>
          </div>
          <Button asChild>
            <Link href={`/admin/merchants/${merchant.id}/deals/new`}>Add deal</Link>
          </Button>
        </div>
        <div className="overflow-x-auto rounded-lg border border-charcoal-700">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-charcoal-700 bg-charcoal-900/40 text-charcoal-400">
              <tr>
                <th className="px-3 py-2 font-medium">Title</th>
                <th className="px-3 py-2 font-medium">Price</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {deals.map((deal) => {
                const title =
                  deal.translations?.[0]?.title?.trim() || "Untitled deal";
                return (
                  <tr key={deal.id} className="border-b border-charcoal-700/60">
                    <td className="px-3 py-2 text-charcoal-50">{title}</td>
                    <td className="px-3 py-2 text-charcoal-300">
                      {deal.currency_code} {deal.deal_price}
                    </td>
                    <td className="px-3 py-2 text-charcoal-300">
                      {deal.is_active ? "active" : "inactive"}
                      {deal.slot_exempt ? " · exempt" : ""}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          className="h-8 px-2 text-xs"
                          onClick={() => onToggleDeal(deal)}
                        >
                          {deal.is_active ? "Deactivate" : "Activate"}
                        </Button>
                        <Button asChild variant="outline" className="h-8 px-2 text-xs">
                          <Link href={`/admin/deals/${deal.id}/edit`}>Edit</Link>
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          className="h-8 px-2 text-xs text-burgundy-600"
                          onClick={() => onDeleteDeal(deal.id, title)}
                        >
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {deals.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-charcoal-400">
                    No deals yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
