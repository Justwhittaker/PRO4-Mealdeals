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
import { TERMS_ACCEPT_COOKIE, TERMS_VERSION } from "@/lib/legal-config";

type AuthMode = "signin" | "register" | "forgot";

function setTermsAcceptCookie(version: string) {
  const maxAge = 60 * 30; // 30 minutes — enough for OAuth round-trip
  document.cookie = `${TERMS_ACCEPT_COOKIE}=${encodeURIComponent(version)}; path=/; max-age=${maxAge}; samesite=lax`;
}

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
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [googleReady, setGoogleReady] = useState<boolean | null>(null);

  const isRegister = mode === "register";
  const isForgot = mode === "forgot";

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
    setAcceptedTerms(false);
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

    if (mode === "register" && !acceptedTerms) {
      setError(
        "Please confirm you have read and agree to the Terms and acknowledge the Privacy Notice.",
      );
      setLoading(false);
      return;
    }

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
      ...(mode === "register"
        ? {
            termsAccepted: "true",
            termsVersion: TERMS_VERSION,
          }
        : {}),
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
    if (isRegister && !acceptedTerms) {
      setError(
        "Please confirm you have read and agree to the Terms and acknowledge the Privacy Notice before continuing with Google.",
      );
      return;
    }
    if (isRegister) {
      setTermsAcceptCookie(TERMS_VERSION);
    }
    setLoading(true);
    await signIn("google", { callbackUrl: "/dashboard" });
  }

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
              {isRegister ? (
                <div className="space-y-3 rounded-md border border-charcoal-700 bg-charcoal-950/40 px-3 py-3">
                  <label className="flex cursor-pointer items-start gap-3 text-left text-sm text-charcoal-200">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 shrink-0 rounded border-charcoal-600"
                      checked={acceptedTerms}
                      onChange={(e) => setAcceptedTerms(e.target.checked)}
                      required
                      aria-required="true"
                    />
                    <span>
                      I have read and agree to the Dine A Deal{" "}
                      <Link
                        href="/terms"
                        className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Terms and Conditions
                      </Link>{" "}
                      and acknowledge the{" "}
                      <Link
                        href="/privacy"
                        className="font-medium text-burgundy-500 underline-offset-2 hover:underline"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Privacy Notice
                      </Link>
                      .
                    </span>
                  </label>
                  <p className="text-xs text-charcoal-500">
                    This agreement is not consent for newsletter, third-party
                    marketing, selling contact details, or promotional texts.
                    Those choices are collected separately where offered
                    (for example on the{" "}
                    <Link
                      href="/newsletter"
                      className="text-burgundy-500 underline-offset-2 hover:underline"
                    >
                      newsletter
                    </Link>{" "}
                    form).
                  </p>
                </div>
              ) : null}
              {error ? <p className="text-sm text-red-500">{error}</p> : null}
              <Button
                type="submit"
                className="w-full"
                disabled={loading || (isRegister && !acceptedTerms)}
              >
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
                disabled={
                  loading ||
                  googleReady === false ||
                  (isRegister && !acceptedTerms)
                }
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
