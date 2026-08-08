"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { submitContactMessage } from "@/lib/api";

export function ContactForm() {
  const [name, setName] = useState("");
  const [surname, setSurname] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [business, setBusiness] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);

    const result = await submitContactMessage({
      name: name.trim(),
      surname: surname.trim(),
      email: email.trim(),
      phone: phone.trim(),
      business: business.trim() || undefined,
      title: title.trim(),
      description: description.trim(),
    });

    setPending(false);
    if (!result.ok) {
      setError(result.error || "Could not send your message. Please try again.");
      return;
    }
    setDone(true);
  }

  if (done) {
    return (
      <div className="border border-charcoal-700 bg-white p-6 shadow-deal">
        <p className="font-display text-xl text-charcoal-50">Message sent</p>
        <p className="mt-2 text-sm text-charcoal-300">
          Thanks — we&apos;ve received your note and will get back to you soon.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={onSubmit}
      className="space-y-4 border border-charcoal-700 bg-white p-6 shadow-deal"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="contact-name">Name</Label>
          <Input
            id="contact-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoComplete="given-name"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="contact-surname">Surname</Label>
          <Input
            id="contact-surname"
            value={surname}
            onChange={(e) => setSurname(e.target.value)}
            required
            autoComplete="family-name"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="contact-email">Email</Label>
        <Input
          id="contact-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="contact-phone">Phone number</Label>
        <Input
          id="contact-phone"
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          required
          autoComplete="tel"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="contact-business">
          Business <span className="text-charcoal-400">(optional)</span>
        </Label>
        <Input
          id="contact-business"
          value={business}
          onChange={(e) => setBusiness(e.target.value)}
          autoComplete="organization"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="contact-title">Title</Label>
        <Input
          id="contact-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          maxLength={200}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="contact-description">Description of issue</Label>
        <textarea
          id="contact-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
          rows={5}
          className="flex w-full rounded-md border border-charcoal-600 bg-white px-3 py-2 text-sm text-charcoal-50 placeholder:text-charcoal-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-burgundy-400/50 disabled:cursor-not-allowed disabled:opacity-50"
        />
      </div>

      {error ? <p className="text-sm text-red-500">{error}</p> : null}

      <Button type="submit" className="w-full" disabled={pending}>
        {pending ? "Sending…" : "Send message"}
      </Button>
    </form>
  );
}
