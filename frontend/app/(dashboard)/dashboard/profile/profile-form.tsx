"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  updateMerchantProfile,
  type MerchantProfile,
} from "@/lib/api";

interface ProfileFormProps {
  merchantId: string;
  initial: MerchantProfile;
}

export function ProfileForm({ merchantId, initial }: ProfileFormProps) {
  const [name, setName] = useState(initial.name);
  const [email, setEmail] = useState(initial.email ?? "");
  const [contactName, setContactName] = useState(initial.contact_name ?? "");
  const [phone, setPhone] = useState(initial.phone ?? "");
  const [website, setWebsite] = useState(initial.website ?? "");
  const [bio, setBio] = useState(initial.bio ?? "");
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState(initial);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setStatus(null);
    const result = await updateMerchantProfile(merchantId, {
      name,
      email: email || undefined,
      contact_name: contactName || undefined,
      phone: phone || undefined,
      website: website || undefined,
      bio: bio || undefined,
    });
    setSaving(false);
    if (!result.ok) {
      setStatus(result.error);
      return;
    }
    setProfile(result.data);
    setStatus("Profile saved.");
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <Card>
        <CardHeader>
          <CardTitle>Venue details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSave} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Business name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Login email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@venue.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact">Contact name</Label>
              <Input
                id="contact"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="website">Website</Label>
                <Input
                  id="website"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="bio">About</Label>
              <textarea
                id="bio"
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                rows={4}
                className="flex w-full rounded-md border border-charcoal-700 bg-charcoal-950 px-3 py-2 text-sm text-charcoal-100 placeholder:text-charcoal-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-citrus-500/40"
              />
            </div>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save profile"}
            </Button>
            {status ? (
              <p className="text-sm text-charcoal-300">{status}</p>
            ) : null}
          </form>
        </CardContent>
      </Card>

      <Card className="border-citrus-500/20">
        <CardHeader>
          <CardTitle>Subscription & slots</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="flex flex-wrap gap-2">
            <Badge variant={profile.is_subscriber ? "default" : "secondary"}>
              {profile.is_subscriber ? "Priority active" : "Not subscribed"}
            </Badge>
            <Badge variant="outline">{profile.subscription_phase}</Badge>
            <Badge variant="outline">{profile.tier_level}</Badge>
          </div>
          <p className="text-charcoal-300">
            <span className="text-citrus-300 font-semibold">
              {profile.active_deal_count}/{profile.deal_slot_limit || 3}
            </span>{" "}
            slots in use ·{" "}
            <span className="text-citrus-300">{profile.open_slots}</span> open
          </p>
          <p className="text-charcoal-400">
            {profile.total_deal_count} deals in history (including past / inactive).
            Deactivate a live deal to free a slot, then repost from history.
          </p>
          {profile.location ? (
            <p className="text-charcoal-500">
              {profile.location.city}, {profile.location.country_code}
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
