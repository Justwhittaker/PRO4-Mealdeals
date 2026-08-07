"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  resolveOrCreateLocation,
  updateMerchantProfile,
  type MerchantProfile,
} from "@/lib/api";
import { lookupCityCoords } from "@/lib/geo";
import { MARKET_COUNTRIES } from "@/lib/markets-catalog";

interface ProfileFormProps {
  merchantId: string;
  initial: MerchantProfile;
}

function matchCountryIso(code?: string | null): string {
  if (!code) return "";
  const upper = code.toUpperCase();
  if (MARKET_COUNTRIES.some((c) => c.iso === upper)) return upper;
  if (upper === "UK") return "GB";
  return upper;
}

export function ProfileForm({ merchantId, initial }: ProfileFormProps) {
  const countries = useMemo(
    () => [...MARKET_COUNTRIES].sort((a, b) => a.label.localeCompare(b.label)),
    [],
  );

  const [name, setName] = useState(initial.name);
  const [email, setEmail] = useState(initial.email ?? "");
  const [contactName, setContactName] = useState(initial.contact_name ?? "");
  const [phone, setPhone] = useState(initial.phone ?? "");
  const [website, setWebsite] = useState(initial.website ?? "");
  const [bio, setBio] = useState(initial.bio ?? "");
  const [countryIso, setCountryIso] = useState(
    matchCountryIso(initial.location?.country_code),
  );
  const [cityLabel, setCityLabel] = useState(initial.location?.city ?? "");
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState(initial);

  const cities = useMemo(() => {
    const country = countries.find((c) => c.iso === countryIso);
    if (!country) return [];
    return [...country.cities].sort((a, b) => a.label.localeCompare(b.label));
  }, [countries, countryIso]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setStatus(null);

    if (!countryIso || !cityLabel.trim()) {
      setSaving(false);
      setStatus("Choose a country and city so we know where your venue is.");
      return;
    }

    const country = countries.find((c) => c.iso === countryIso);
    const cityOption = cities.find(
      (c) => c.label.toLowerCase() === cityLabel.trim().toLowerCase(),
    );
    const coords =
      lookupCityCoords(country?.code ?? countryIso, cityOption?.city ?? cityLabel) ??
      { lat: 0, lon: 0 };

    const location = await resolveOrCreateLocation({
      countryCode: countryIso,
      city: cityLabel.trim(),
      latitude: coords.lat,
      longitude: coords.lon,
    });
    if (!location.ok) {
      setSaving(false);
      setStatus(location.error);
      return;
    }

    const result = await updateMerchantProfile(merchantId, {
      name,
      email: email || undefined,
      contact_name: contactName || undefined,
      phone: phone || undefined,
      website: website || undefined,
      bio: bio || undefined,
      location_id: location.data.id,
    });
    setSaving(false);
    if (!result.ok) {
      setStatus(result.error);
      return;
    }
    setProfile(result.data);
    setCountryIso(matchCountryIso(result.data.location?.country_code) || countryIso);
    setCityLabel(result.data.location?.city ?? cityLabel);
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
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Country</Label>
                <Select
                  value={countryIso || undefined}
                  onValueChange={(value) => {
                    setCountryIso(value);
                    setCityLabel("");
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select country" />
                  </SelectTrigger>
                  <SelectContent className="max-h-72">
                    {countries.map((country) => (
                      <SelectItem key={country.iso} value={country.iso}>
                        {country.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>City</Label>
                <Select
                  value={cityLabel || undefined}
                  onValueChange={setCityLabel}
                  disabled={!countryIso}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select city" />
                  </SelectTrigger>
                  <SelectContent className="max-h-72">
                    {cities.map((city) => (
                      <SelectItem key={`${city.country}-${city.city}`} value={city.label}>
                        {city.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
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
          ) : (
            <p className="text-amber-200">
              Add your country and city so deals show in the right area.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
