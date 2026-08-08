import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import GoogleProvider from "next-auth/providers/google";
import { resolveMerchantIdForEmail } from "@/lib/merchant-bootstrap";

function parseAdminEmails(): Set<string> {
  const raw = process.env.ADMIN_EMAILS ?? "";
  return new Set(
    raw
      .split(",")
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean),
  );
}

function isAdminCredentials(email: string, password: string): boolean {
  const allowed = parseAdminEmails();
  const adminPassword = process.env.ADMIN_PASSWORD ?? "";
  if (!allowed.size || !adminPassword) return false;
  return allowed.has(email.trim().toLowerCase()) && password === adminPassword;
}

/**
 * Merchant login — links email to a Postgres profile (creates one if needed).
 * Admin login — separate credentials provider gated by ADMIN_EMAILS + ADMIN_PASSWORD.
 */
export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      id: "admin-login",
      name: "Admin Login",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials.password) return null;
        if (!isAdminCredentials(credentials.email, credentials.password)) {
          return null;
        }
        return {
          id: "admin",
          email: credentials.email.trim().toLowerCase(),
          name: "Admin",
          role: "admin",
        } as { id: string; email: string; name: string; role: "admin" };
      },
    }),
    CredentialsProvider({
      id: "credentials",
      name: "Merchant Login",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email) return null;
        if (!credentials.password) return null;

        // Never treat admin-only accounts as merchants via this provider
        const allowedAdmins = parseAdminEmails();
        if (
          allowedAdmins.has(credentials.email.trim().toLowerCase()) &&
          process.env.ADMIN_PASSWORD &&
          credentials.password === process.env.ADMIN_PASSWORD
        ) {
          return null;
        }

        const merchantId = await resolveMerchantIdForEmail(credentials.email);
        if (!merchantId) return null;

        return {
          id: merchantId,
          email: credentials.email,
          name: credentials.email.split("@")[0] ?? "Merchant",
          role: "merchant",
        } as { id: string; email: string; name: string; role: "merchant" };
      },
    }),
    ...(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET
      ? [
          GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET,
            allowDangerousEmailAccountLinking: true,
          }),
        ]
      : []),
  ],
  pages: {
    signIn: "/dashboard",
    error: "/dashboard",
  },
  session: {
    strategy: "jwt",
  },
  secret:
    process.env.NEXTAUTH_SECRET ||
    process.env.AUTH_SECRET ||
    "dineadeal-dev-nextauth-secret-change-me",
  callbacks: {
    async jwt({ token, user, account }) {
      if (user) {
        const role =
          (user as { role?: string }).role === "admin" ? "admin" : "merchant";
        token.role = role;

        if (role === "admin") {
          token.merchantId = undefined;
          return token;
        }

        if (account?.provider === "credentials") {
          token.merchantId = user.id;
        } else if (user.email) {
          const merchantId = await resolveMerchantIdForEmail(user.email);
          token.merchantId = merchantId ?? user.id;
        } else {
          token.merchantId = user.id;
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.role = token.role === "admin" ? "admin" : "merchant";
        if (token.role === "admin") {
          session.user.id = "admin";
        } else {
          session.user.id = (token.merchantId as string) ?? token.sub ?? "";
        }
      }
      return session;
    },
  },
};
