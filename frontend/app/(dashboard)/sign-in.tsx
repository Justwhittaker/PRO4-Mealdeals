"use client";

import { getProviders, signIn } from "next-auth/react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { requestPasswordReset } from "@/lib/api";

type AuthMode = "signin" | "register" | "forgot";

export function DashboardSignIn() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialMode: AuthMode =
    searchParams.get("register") === "1"
      ? "register"
      : searchParams.get("forgot") === "1"
        ? "forgot"
        : "signin";

  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [googleReady, setGoogleReady] = useState<boolean | null>(null);

  useEffect(() => {
    void getProviders().then((providers) => {
      setGoogleReady(Boolean(providers?.google));
    });
  }, []);

  useEffect(() => {
    const authError = searchParams.get("error");
    if (!authError) return;
    if (authError === "OAuthSignin" || authError === "OAuthCallback") {
      setError(
        "Google sign-in failed. Check GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET and the OAuth redirect URI.",
      );
      return;
    }
    if (authError === "OAuthAccountNotLinked") {
      setError(
        "That Google email is already linked another way. Sign in with email/password, or use the same Google account.",
      );
      return;
    }
    setError("Sign-in failed. Please try again.");
  }, [searchParams]);

  function switchMode(next: AuthMode) {
    setMode(next);
    setError(null);
    setInfo(null);
    setConfirmPassword("");
    if (next !== "forgot") {
      setPassword("");
    }
  }

  async function onForgotSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);

    const result = await requestPasswordReset(email.trim());
    setLoading(false);
    if (!result.ok) {
      setError(result.error || "Could not send reset email. Try again.");
      return;
    }
    setInfo(result.data.message);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);

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

  async function onGoogle() {
    setError(null);
    if (googleReady === false) {
      setError(
        "Google sign-in is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the frontend env, then restart Next.js.",
      );
      return;
    }
    setLoading(true);
    await signIn("google", { callbackUrl: "/dashboard" });
  }

  const isRegister = mode === "register";
  const isForgot = mode === "forgot";

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-6 px-3 py-10 text-center sm:px-6 sm:py-16 sm:text-left">
      <div>
        <h1 className="font-display text-3xl text-charcoal-50">
          {isForgot
            ? "Forgot password"
            : isRegister
              ? "Create account"
              : "Merchant Sign in"}
        </h1>
        <p className="mt-2 text-charcoal-400">
          {isForgot
            ? "Enter your merchant email and we’ll send reset instructions."
            : isRegister
              ? "Create an account to list deals and manage billing."
              : "Sign in to manage deals and billing."}
        </p>
      </div>
      <Card className="text-left">
        <CardHeader>
          <CardTitle>
            {isForgot
              ? "Reset password"
              : isRegister
                ? "Create account"
                : "Merchant Sign in"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isForgot ? (
            <form onSubmit={onForgotSubmit} className="space-y-4">
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
              {error ? <p className="text-sm text-red-500">{error}</p> : null}
              {info ? <p className="text-sm text-burgundy-600">{info}</p> : null}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Sending…" : "Send reset instructions"}
              </Button>
              <p className="text-center text-sm text-charcoal-400">
                <button
                  type="button"
                  className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
                  onClick={() => switchMode("signin")}
                >
                  Back to Merchant Sign in
                </button>
              </p>
            </form>
          ) : (
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
                <div className="flex items-center justify-between gap-3">
                  <Label htmlFor="password">Password</Label>
                  {!isRegister ? (
                    <button
                      type="button"
                      className="text-xs font-medium text-burgundy-500 underline-offset-2 hover:underline"
                      onClick={() => switchMode("forgot")}
                    >
                      Forgot password?
                    </button>
                  ) : null}
                </div>
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
                disabled={loading || googleReady === false}
                onClick={() => void onGoogle()}
              >
                Continue with Google
              </Button>
              {googleReady === false ? (
                <p className="text-xs text-charcoal-400">
                  Google sign-in needs{" "}
                  <code className="text-charcoal-200">GOOGLE_CLIENT_ID</code> and{" "}
                  <code className="text-charcoal-200">GOOGLE_CLIENT_SECRET</code>{" "}
                  in the frontend env. Redirect URI:{" "}
                  <code className="text-charcoal-200">
                    {"{NEXTAUTH_URL}/api/auth/callback/google"}
                  </code>
                  .{" "}
                  <Link href="/contact" className="text-burgundy-500 hover:underline">
                    Contact us
                  </Link>{" "}
                  if you need help.
                </p>
              ) : null}
            </form>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
