"use client";

import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type AuthMode = "signin" | "register";

export function DashboardSignIn() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialMode: AuthMode =
    searchParams.get("register") === "1" ? "register" : "signin";

  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState(
    initialMode === "signin" ? "merchant@dineadeal.demo" : "",
  );
  const [password, setPassword] = useState(initialMode === "signin" ? "demo" : "");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function switchMode(next: AuthMode) {
    setMode(next);
    setError(null);
    setConfirmPassword("");
    if (next === "register") {
      setEmail("");
      setPassword("");
    } else {
      setEmail("merchant@dineadeal.demo");
      setPassword("demo");
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (mode === "register" && password !== confirmPassword) {
      setError("Passwords do not match.");
      setLoading(false);
      return;
    }

    if (mode === "register" && password.length < 4) {
      setError("Choose a password with at least 4 characters.");
      setLoading(false);
      return;
    }

    const res = await signIn("credentials", {
      email,
      password,
      redirect: false,
      callbackUrl: "/dashboard",
    });

    if (!res || res.error) {
      const hint =
        res?.error === "Configuration"
          ? "Auth is misconfigured (missing NEXTAUTH_SECRET)."
          : mode === "register"
            ? "Could not create account. Check your connection and try again."
            : "Sign-in failed. Check email/password and try again.";
      setError(hint);
      setLoading(false);
      return;
    }

    router.push(res.url || "/dashboard");
    router.refresh();
  }

  const isRegister = mode === "register";

  return (
    <main className="mx-auto flex max-w-md flex-col gap-6 px-4 py-16 sm:px-6">
      <div>
        <h1 className="font-display text-3xl text-charcoal-50">
          Merchant Sign in
        </h1>
        <p className="mt-2 text-charcoal-400">
          {isRegister
            ? "Create an account to list deals and manage billing."
            : "Sign in to manage deals and billing. Demo credentials work with any password."}
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>
            {isRegister ? "Create account" : "Merchant Sign in"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete={isRegister ? "new-password" : "current-password"}
              />
              {!isRegister ? (
                <p className="text-sm text-charcoal-400">
                  New business?{" "}
                  <button
                    type="button"
                    className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
                    onClick={() => switchMode("register")}
                  >
                    Register a new account &amp; get the first month Free
                  </button>
                </p>
              ) : null}
            </div>
            {isRegister ? (
              <div className="space-y-2">
                <Label htmlFor="confirm">Confirm password</Label>
                <Input
                  id="confirm"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                />
                <p className="text-sm text-charcoal-400">
                  Already have an account?{" "}
                  <button
                    type="button"
                    className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
                    onClick={() => switchMode("signin")}
                  >
                    Merchant Sign in
                  </button>
                </p>
              </div>
            ) : null}
            {error ? <p className="text-sm text-red-500">{error}</p> : null}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading
                ? isRegister
                  ? "Creating account…"
                  : "Signing in…"
                : isRegister
                  ? "Create account"
                  : "Merchant Sign in"}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
            >
              Continue with Google
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
