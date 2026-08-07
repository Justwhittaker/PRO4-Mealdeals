import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import GoogleProvider from "next-auth/providers/google";
import { resolveMerchantIdForEmail } from "@/lib/merchant-bootstrap";

/**
 * Merchant login — links email to a Postgres profile (creates one if needed).
 */
export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Merchant Login",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email) return null;

        // Stub: accept any non-empty password for local demo
        if (!credentials.password) return null;

        const merchantId = await resolveMerchantIdForEmail(credentials.email);
        if (!merchantId) return null;

        return {
          id: merchantId,
          email: credentials.email,
          name: credentials.email.split("@")[0] ?? "Merchant",
        };
      },
    }),
    ...(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET
      ? [
          GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET,
          }),
        ]
      : []),
  ],
  pages: {
    signIn: "/dashboard",
  },
  session: {
    strategy: "jwt",
  },
  secret: process.env.NEXTAUTH_SECRET,
  callbacks: {
    async jwt({ token, user, account }) {
      if (user) {
        // Credentials already resolve Postgres merchant id in authorize().
        // Google (and other OAuth) must link/create a profile by email.
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
        session.user.id = (token.merchantId as string) ?? token.sub ?? "";
      }
      return session;
    },
  },
};
